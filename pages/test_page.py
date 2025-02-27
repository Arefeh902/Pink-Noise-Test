import time
import threading
import csv
from queue import Queue
from pathlib import Path
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QEvent
from PyQt6.QtGui import QCursor, QPainter, QColor, QPen, QTabletEvent
from PyQt6.QtWidgets import QWidget
from models import Data, TabletData
from config import (
	BACKGROUND_COLOR, SOURCE_CIRCLE_COLOR, DESTINATION_CIRCLE_COLOR, RECT_COLOR,
	SUCCESS_PATH_COLOR, FAILURE_PATH_COLOR, START_FREQUENCY, START_DURATION_MS,
	SUCCESS_FREQUENCY, SUCCESS_DURATION_MS, FAILURE_FREQUENCY, FAILURE_DURATION_MS, 
	DELAY_BETWEEN_TESTS, MAX_NUM_OF_ADDITIONAL_RCORDED_POINTS
)
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
import sounddevice as sd
import numpy as np
import os

######################################################################################
#                                                                                    #
#                                Manager Page                                        #
#                                                                                    #
######################################################################################

class PageManager(QObject):
	"""Manages the test progression and navigation between pages."""
	start_test_signal = pyqtSignal(Data)
	finished_signal = pyqtSignal()

	def __init__(self, file_path: str):
		super().__init__()
		self.file_path = file_path
		self.test_number = 0
		self.data_generator = self._data_generator_function()

	def _data_generator_function(self):
		"""Generator function to read test data from a CSV file."""
		from config import INDEX_OF_START_TEST
		with open(self.file_path, 'r') as file:
			csv_reader = csv.reader(file)
			for row in csv_reader:
				self.test_number += 1
				if self.test_number < INDEX_OF_START_TEST:
					continue
				yield self._parse_row(row)

	def _parse_row(self, row: list) -> Data:
		"""Parses a row of CSV data into a Data object."""
		data = [float(x) for x in row]
		time, rate = int(data[0]), int(data[1])
		circle_size = 3
		rectangle_size = 4

		source_circle = tuple(data[2:2 + circle_size])
		dest_circle = tuple(data[2 + circle_size:2 + 2 * circle_size])

		index = 2 + 2 * circle_size
		num_middle_circles = int(data[index])
		middle_circles = [
			tuple(data[i:i + circle_size])
			for i in range(index + 1, index + 1 + num_middle_circles * circle_size, circle_size)
		]

		index += 1 + num_middle_circles * circle_size
		num_rectangles = int(data[index])
		rectangles = [
			tuple(data[i:i + rectangle_size])
			for i in range(index + 1, index + 1 + num_rectangles * rectangle_size, rectangle_size)
		]

		return Data(time, rate, source_circle, dest_circle, middle_circles, rectangles, 75)

	def start_tests(self):
		"""Starts the test sequence."""
		self.next_test()

	def next_test(self):
		try:
			data = next(self.data_generator)
			self.start_test_signal.emit(data)
		except StopIteration:
			self.finished_signal.emit()



def play_beep(frequency: float, duration: float):
	# Generate a sine wave
	sample_rate = 44100  # Samples per second (standard for audio)
	t = np.linspace(0, duration, int(sample_rate * duration), False)
	audio = np.sin(2 * np.pi * frequency * t)

	# Play the audio
	sd.play(audio, samplerate=sample_rate)
	sd.wait()

class TestPage(QWidget):
	"""Handles a single test, managing input, drawing, and logic."""
	def __init__(self, data: Data, target_dir: str, target_file_prefix: str, manager: PageManager):
		super().__init__()
		self.data = data
		self.state = self.data.state
		self.manager = manager
		self.target_dir = target_dir
		self.target_file_prefix = target_file_prefix
		self.is_running = False

		self.sampling_rate_ms = 1000 / self.data.rate
		self.read_queue = Queue(maxsize=10000)
		self.tablet_data_times = []

		self.start_time = 0
		self.tablet_data = None
		self.tablet_connected = False
		self.path_color = FAILURE_PATH_COLOR
		self.show_path_flag = False

		self.setFixedSize(self.data.dimensions.WINDOW_WIDTH_PIXELS, self.data.dimensions.WINDOW_HEIGHT_PIXELS)
		self.setWindowTitle("Circles Display")
		
		self.init_ui()
		
		self.reading_thread = threading.Thread(target=self.read_data)
		self.processing_thread = threading.Thread(target=self.process_data)
  
		self.start_beep_thread = threading.Thread(target=play_beep, args=(START_FREQUENCY, START_DURATION_MS))
		self.success_beep_thread = threading.Thread(target=play_beep, args=(SUCCESS_FREQUENCY, SUCCESS_DURATION_MS))
		self.failure_beep_thread = threading.Thread(target=play_beep, args=(FAILURE_FREQUENCY, FAILURE_DURATION_MS))
	
	def init_ui(self):
		layout = QVBoxLayout()
		layout.addStretch()

		# Create a QLabel for the test number at the bottom
		self.test_number_label = QLabel(f"Test Number: {self.manager.test_number}")
		self.test_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

		# Style the label to make it small and subtle
		self.test_number_label.setStyleSheet("""
			font-size: 20px;
			color: #555555;
			padding: 5px;
		""")

		layout.addWidget(self.test_number_label, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
		self.setLayout(layout)
		
	def tabletEvent(self, event: QTabletEvent):
		"""Handles tablet input events."""
		# threading.Thread(target=self.tablet_, args=(event, time.perf_counter_ns())).start()
		# current_time = time.perf_counter_ns()
		self.tablet_data = [
			event.position().x(),
			event.position().y(),
			event.pressure(),
			event.xTilt(),
			event.yTilt(),
			event.rotation(),
			event.timestamp()
		]
		
		if not self.start_time and event.type() == QEvent.Type.TabletPress and self.data.source_circle.check_hit(event.position().x(), event.position().y()):
			self.tablet_connected = True
			self.start_tracking()
			

	def mousePressEvent(self, event):
		"""Handles mouse press events."""
		if not self.start_time and self.data.source_circle.check_hit(event.position().x(), event.position().y()):
			self.start_tracking()


	def start_tracking(self):
		"""Starts tracking user input."""
		self.start_time = time.perf_counter_ns()
		self.is_running = True

		self.reading_thread.start()
		self.processing_thread.start()
		self.start_beep_thread.start()
		

	def read_data(self):
		"""Reads input data from the mouse or tablet at regular intervals."""
		last_sample_time = self.start_time
		while self.is_running:
			current_time = time.perf_counter_ns()
			if current_time - last_sample_time > self.sampling_rate_ms * 1e6:
				last_sample_time = current_time
				if self.tablet_connected:
					data = self.tablet_data.copy()
				else:
					pos = self.mapFromGlobal(QCursor.pos())
					data = [pos.x(), pos.y(), None, None, None, None, None]
				elapsed_time = (current_time - self.start_time) / 1e6
				self.read_queue.put((data, elapsed_time))


	def process_data(self):
		"""Processes the sampled input data."""
		while self.is_running:
			if not self.read_queue.empty():
				data, t = self.read_queue.get()
				x, y = data[0], data[1]
				if self.check_end_test(x, y, t):
					self.start_stop_thread(t)

				self.data.process_input_data(data, t)

		count = MAX_NUM_OF_ADDITIONAL_RCORDED_POINTS
		while not self.read_queue.empty() and count > 0:
			data, t = self.read_queue.get()
			self.data.process_input_data(data, t)
			count -= 1

	def check_end_test(self, x, y, t) -> bool:
		"""Checks if the test should end based on input conditions."""
		dest = self.data.dest_circle
		if t >= self.data.time_to_finish:
			return True
		if self.data.state.dest_hit:
			return True
		if x - (dest.x + dest.rx) >= self.data.passing_offset * self.data.dimensions.X_CM_TO_PIXEL:
			self.data.state.dest_passed = 1
			return True
		return False
		
	def start_stop_thread(self, t):
		self.is_running = False
		self.stop_thread = threading.Thread(target=self.stop_tracking, args=(t,))
		self.stop_thread.start()
			

	def stop_tracking(self, t):
		print("Tracking stopped!")
		self.data.state.time = t
		self.state.success_status = self.determine_status()

		if self.reading_thread.is_alive():
			self.reading_thread.join() 
		if self.processing_thread.is_alive():
			self.processing_thread.join()

		self.path_color = SUCCESS_PATH_COLOR if self.state.success_status else FAILURE_PATH_COLOR
		if self.state.success_status:
			self.success_beep_thread.start()
		else:
			self.failure_beep_thread.start()

		self.show_path_flag = True
		self.update()

		QTimer.singleShot(DELAY_BETWEEN_TESTS, self.manager.next_test)
  
		self.save_data()

	def determine_status(self) -> bool:
		"""Determines the success status of the test."""
		if self.data.state.time > self.data.time_to_finish:
			return False
		if not self.data.state.dest_hit:
			return False
		if any(not hit for hit in self.data.state.circles_hit):
			return False
		if any(self.data.state.rects_hit):
			return False
		return True

	def generate_header_and_first_row(self):
		"""Generates the header and first row for the CSV file."""
		header = ['x', 'y', 'pressure', 'x_tilt', 'y_tilt', 'rotation', 'tablet_time', 'time', 'total_time', 'success', 'timeout', 'dest_passed', 'source_hit', 'dest_hit']
		header += [f"circle_{i + 1}_hit" for i in range(len(self.data.state.circles_hit))]
		header += [f"rect_{i + 1}_hit" for i in range(len(self.data.state.rects_hit))]
		header += [f'distance of last point from center of dest']

		first_row = [
			*self.data.state.points[0],
			self.data.state.time,
			int(self.data.state.success_status),
			int(self.data.state.time > self.data.time_to_finish),
			self.data.state.dest_passed,
			self.data.state.source_hit,
			self.data.state.dest_hit,
			*self.data.state.circles_hit,
			*self.data.state.rects_hit,
			self.data.dest_circle.calc_dist_to_center(self.data, self.data.state.points[-1][0], self.data.state.points[-1][1])
		]
		return header, first_row

	def save_data(self):
		print('saving data...')
		"""Saves the test data to a CSV file."""
		output_path = Path(self.target_dir) / f"{self.target_file_prefix}_{self.manager.test_number}.csv"
		with output_path.open(mode="w", newline="") as file:
			writer = csv.writer(file)
			header, first_row = self.generate_header_and_first_row()
			writer.writerow(header)
			writer.writerow(first_row)
			writer.writerows(self.data.state.points[1:])

	def paintEvent(self, event):
		"""Handles custom painting of the test elements."""
		painter = QPainter(self)
		painter.fillRect(self.rect(), QColor(*BACKGROUND_COLOR))

		# Draw source, destination, and middle circles
		self.data.source_circle.draw(painter)
		self.data.dest_circle.draw(painter)
		for circle in self.data.middle_circles:
			circle.draw(painter)

		# Draw rectangles
		for rect in self.data.rects:
			rect.draw(painter)

		# Draw path if the flag is set
		if self.show_path_flag:
			pen = QPen(QColor(*self.path_color), 2)
			painter.setPen(pen)
			for i in range(len(self.data.state.points) - 1):
				if self.data.state.points[i+1][-1] > self.data.state.time:
					break
				x1, y1 = self.data.state.points[i][:2]
				x1, y1 = self.data.reverse_process_x_and_y_for_record(x1, y1) 
				x2, y2 = self.data.state.points[i+1][:2]
				x2, y2 = self.data.reverse_process_x_and_y_for_record(x2, y2) 
				painter.drawLine(
					int(x1), int(y1),
					int(x2), int(y2)
					# int(self.data.state.points[i][0]),
					# int(self.data.state.points[i][1]),
					# int(self.data.state.points[i + 1][0]),
					# int(self.data.state.points[i + 1][1]),
				)

