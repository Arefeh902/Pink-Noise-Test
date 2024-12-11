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
	DELAY_BETWEEN_TESTS
)
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
import sounddevice as sd
import numpy as np

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
			tuple(data[i:i + 6])
			for i in range(index + 1, index + 1 + num_rectangles * 6, 6)
		]

		return Data(time, rate, source_circle, dest_circle, middle_circles, rectangles)

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
	def __init__(self, data: Data, target_dir: str, manager: PageManager):
		super().__init__()
		self.data = data
		self.data.dimensions.WINDOW_HEIGHT_PIXELS -= 250
		self.data.dimensions.WINDOW_WIDTH_PIXELS -= 250
		self.state = self.data.state
		self.manager = manager
		self.target_dir = target_dir
		self.is_running = False

		self.sampling_rate_ms = 1000 / self.data.rate
		self.sampling_rate_ms = 5
		self.read_queue = Queue(maxsize=10000)
		self.tablet_data_times = []

		self.start_time = None
		self.tablet_data = None
		self.tablet_connected = False
		self.path_color = FAILURE_PATH_COLOR
		self.show_path_flag = False

		self.setGeometry(0, 0, data.dimensions.WINDOW_WIDTH_PIXELS, data.dimensions.WINDOW_HEIGHT_PIXELS)
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
		current_time = time.perf_counter_ns()
		if not self.start_time and event.type() == QEvent.Type.TabletPress and self.data.source_circle.check_hit(event.position().x(), event.position().y()):
			# self.start_tracking()		
			self.start_time = time.perf_counter_ns()
			self.is_running = True

			# self.reading_thread.start()
			self.processing_thread.start()
			self.start_beep_thread.start()

		if self.is_running:
			# print(time.perf_counter_ns() / 1e6)
			self.tablet_data_times.append((current_time - self.start_time) / 1e6)
			tablet_thread = threading.Thread(target=self.tablet_, args=(event, current_time))
			tablet_thread.start()


	def tablet_(self, event, current_time):
		self.tablet_connected = True
		starting_time = self.start_time if self.start_time else current_time
		self.tablet_data = [
			event.position().x(),
			event.position().y(),
			event.pressure(),
			event.xTilt(),
			event.yTilt(),
			event.rotation(),
			(current_time - starting_time)/ 1e6
		]
		
		# elapsed_time = time.perf_counter_ns() - starting_time
		elapsed_time = current_time - starting_time
		self.read_queue.put((self.tablet_data, elapsed_time))
	
   

	def mousePressEvent(self, event):
		"""Handles mouse press events."""
		if not self.tablet_connected and not self.start_time and self.data.source_circle.check_hit(event.position().x(), event.position().y()):
			self.start_tracking()


	def start_tracking(self):
		"""Starts tracking user input."""
		self.start_time = time.perf_counter_ns()
		self.is_running = True

		# self.reading_thread.start()
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

				elapsed_time = time.perf_counter_ns() - self.start_time
				self.read_queue.put((data, elapsed_time))


	def process_data(self):
		"""Processes the sampled input data."""
		while self.is_running:
			if not self.read_queue.empty():
				data, t = self.read_queue.get()
				self.data.process_input_data(data, t)

				x, y = data[0], data[1]
				if self.check_end_test(x, y, t):
					self.start_stop_thread(t)
		while not self.read_queue.empty():
			data, t = self.read_queue.get()
			self.data.process_input_data(data, t)

	def check_end_test(self, x, y, t) -> bool:
		"""Checks if the test should end based on input conditions."""
		dest = self.data.dest_circle
		if t >= self.data.time_to_finish * 1e6:
			return True
		if self.data.state.dest_hit:
			return True
		if x - (dest.x + dest.rx) >= self.data.passing_offset * self.data.dimensions.X_CM_TO_PIXEL: 
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
			self.reading_thread.join()  # Wait for reading thread to finish
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
		if self.data.state.time > self.data.time_to_finish * 1e6:
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
		header = ['x', 'y', 'pressure', 'x_tilt', 'y_tilt', 'rotation', 'tablet_time', 'time', 'tota_time', 'success', 'timeout', 'source_hit', 'dest_hit']
		header += [f"circle_{i + 1}_hit" for i in range(len(self.data.state.circles_hit))]
		header += [f"rect_{i + 1}_hit" for i in range(len(self.data.state.rects_hit))]

		first_row = [
			*self.data.state.points[0],
			self.data.state.success_status,
			int(self.data.state.time > self.data.time_to_finish * 1e6),
			self.data.state.source_hit,
			self.data.state.dest_hit,
			*self.data.state.circles_hit,
			*self.data.state.rects_hit
		]
		return header, first_row

	def save_data(self):
		print('saving data...')
		"""Saves the test data to a CSV file."""
		output_path = Path(self.target_dir) / f"{self.manager.test_number}.csv"
		with output_path.open(mode="w", newline="") as file:
			writer = csv.writer(file)
			header, first_row = self.generate_header_and_first_row()
			writer.writerow(header)
			writer.writerow(first_row)
			writer.writerows(self.data.state.points[1:])
		self.save_diffs()

	def save_diffs(self):
		output_path = Path(self.target_dir) / f"{self.manager.test_number}_diffs.txt"
		output_time_path = Path(self.target_dir) / f"{self.manager.test_number}_tablet_times.txt"
		
		with output_path.open(mode='w', newline='') as file:
			for i in range(1, len(self.state.points)):
				file.write(f"{self.state.points[i][-1] - self.state.points[i-1][-1]}\n")
		
		with output_time_path.open(mode='w', newline='') as file:
			for i in range(len(self.tablet_data_times)):
				file.write(f"{self.tablet_data_times[i]}\n")


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
				painter.drawLine(
					int(self.data.state.points[i][0]),
					int(self.data.state.points[i][1]),
					int(self.data.state.points[i + 1][0]),
					int(self.data.state.points[i + 1][1]),
				)

