import time
from PyQt6.QtWidgets import (
QApplication, QWidget, QLabel, QLineEdit, QComboBox, QSpinBox,
QRadioButton, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QButtonGroup
)
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QTimer, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import QCursor, QTabletEvent
from models import Data, TabletData, State, ScreenDimensions
from config import BACKGROUND_COLOR, SOURCE_CIRCLE_COLOR, MIDDLE_CIRCLE_COLOR, DESTINATION_CIRCLE_COLOR, RECT_COLOR
import sys
from config import DELAY_BETWEEN_TESTS
import csv
from pathlib import Path
import threading
import pysine
######################################################################################
#                                                                                    #
#                                Manager Page                                        #
#                                                                                    #
######################################################################################

class PageManager(QObject):
	start_test_signal = pyqtSignal(Data)  # Signal to start a TestPage
	finished_signal = pyqtSignal()         # Signal to notify all tests are completed

	def __init__(self, file_path):
		super().__init__()
		self.file_path = file_path
		self.data_generator = self.data_generator_function(self.file_path)
		self.test_number = 0


	def get_data_from_input_row(self, row):
		data = [float(x) for x in row]

		# Read fixed fields
		time = int(data[0])
		rate = int(data[1])

		circle_size = 3
		source_circle = tuple(data[2:2+circle_size])
		dest_circle = tuple(data[2+circle_size:2+2*circle_size])

		# Parse middle circles
		index = 2 + 2 * circle_size
		num_middle_circles = int(data[index])
		middle_circles = []
		index += 1
		for _ in range(num_middle_circles):
			middle_circles.append(tuple(data[index:index + circle_size]))
			index += circle_size

		# Parse rectangles
		rectangle_size = 6
		num_rectangles = int(data[index])
		index += 1
		rectangles = []
		for _ in range(num_rectangles):
			rectangles.append(tuple(data[index:index + rectangle_size]))
			index += rectangle_size

		return Data(time, rate, source_circle, dest_circle, middle_circles, rectangles)


	def data_generator_function(self, file_path):
		# Generator function to read a CSV file row by row
		from config import INDEX_OF_START_TEST
		with open(file_path, 'r') as file:
			csv_reader = csv.reader(file)
			for row in csv_reader:
				self.test_number += 1
				if(self.test_number < INDEX_OF_START_TEST):
					continue
				yield self.get_data_from_input_row(row)


	def start_tests(self):
		self.next_test()

	def next_test(self):
		try:
			data = next(self.data_generator)
			self.start_test_signal.emit(data, )  # Emit signal to create a TestPage
		except StopIteration:
			self.finished_signal.emit()



from config import (
	SUCCESS_PATH_COLOR, FAILURE_PATH_COLOR,
	START_FREQUENCY, START_DURATION_MS,
	SUCCESS_FREQUENCY, SUCCESS_DURATION_MS,
	FAILURE_FREQUENCY, FAILURE_DURATION_MS
	)

import threading
import time
from queue import Queue

def play_beep(frequency=440.0, duration=1.0):
	pysine.sine(frequency, duration)

class TestPage(QWidget):
	def __init__(self, data: Data, target_dir: str, manager=None):
		super().__init__()
		self.data = data
		self.state = self.data.state
		self.target_dir = target_dir
		self.manager = manager
		self.setWindowTitle("Circles Display")
		# self.setFixedSize(data.dimensions.WINDOW_WIDTH_PIXELS, data.dimensions.WINDOW_HEIGHT_PIXELS)
		self.setGeometry(0, 0, data.dimensions.WINDOW_WIDTH_PIXELS, data.dimensions.WINDOW_HEIGHT_PIXELS)
		
		self.sampling_rate_ms = 5  # Sampling every 1 ms
	
		self.read_queue = Queue(maxsize=10000)  # Queue to pass data from read thread to process thread
		self.reading_thread = threading.Thread(target=self.read_data)
		self.processing_thread = threading.Thread(target=self.process_data)
		self.drawing_thread = threading.Thread(target=self.move_rects)
		self.is_running = False  # Flag to control thread execution

		self.start_time = None
		self.tablet_connected = False
		self.path_color = FAILURE_PATH_COLOR
		self.show_path_flag = False
		self.table_data = None
  
		self.start_beep_thread = threading.Thread(target=play_beep, args=(START_FREQUENCY, START_DURATION_MS))
		self.success_beep_thread = threading.Thread(target=play_beep, args=(SUCCESS_FREQUENCY, SUCCESS_DURATION_MS))
		self.failure_beep_thread = threading.Thread(target=play_beep, args=(FAILURE_FREQUENCY, FAILURE_DURATION_MS))
		
	def tabletEvent(self, event: QTabletEvent):
		self.tablet_connected = True
		x = event.position().x()
		y = event.position().y()
		p = event.pressure()
  
		self.tablet_data = TabletData(x, y, p)

		if event.type() == QEvent.Type.TabletPress and self.data.source_circle.check_hit(self.tablet_data.x, self.tablet_data.y) and not self.start_time:
			self.start_tracking()
   
	def mousePressEvent(self, event):
		if not self.tablet_connected and not self.start_time:
			self.start_tracking()


	def start_tracking(self):
		self.start_time = time.perf_counter_ns()
		self.is_running = True
		self.reading_thread.start()
		self.processing_thread.start()
		self.drawing_thread.start()
		self.start_beep_thread.start()

	def read_data(self):
		"""Samples tablet/mouse positions at precise intervals."""
		last_sample_time = self.start_time
		while self.is_running:
			current_time = time.perf_counter_ns()
			if current_time - last_sample_time > self.sampling_rate_ms * 1e6:
				last_sample_time = current_time
				if self.tablet_connected:
					x, y, p = self.tablet_data.return_data()
				else:
					global_mouse_pos = QCursor.pos()
					local_mouse_pos = self.mapFromGlobal(global_mouse_pos)
					x, y, p = local_mouse_pos.x(), local_mouse_pos.y(), None

				elapsed_time = time.perf_counter_ns() - self.start_time
				self.read_queue.put((x, y, p, elapsed_time))
			# print(elapsed_time / 1e6, x, y, p, sep='\t')

			# time.sleep(1 / 1e9)
			# Maintain precise timing
			# time.sleep(max(0, self.sampling_rate_ms / 1000 - (time.perf_counter_ns() - local_start_time) / 1e9))


	def process_data(self):
		"""Processes sampled positions."""
		while self.is_running or not self.read_queue.empty():
			if not self.read_queue.empty():
				x, y, p, t = self.read_queue.get()
				self.data.process_new_point(x, y, p, t)
				# print(t, x, y, p,"Processed!", sep='\t')

				# check for complition
				if self.is_running and self.check_end_test(x, y, t):
					self.start_stop_thread(t)
			

	def check_end_test(self, x, y, t):
		dest = self.data.dest_circle
		dx, dy, drx, dry = dest.x, dest.y, dest.rx, dest.ry
		if t >= self.data.time_to_finish * 10 ** 6:
			return 1
		elif self.data.state.dest_hit:
			return 1
		elif x - (dx + drx) >= self.data.passing_offset * self.data.dimensions.X_CM_TO_PIXEL: 
			return 1
		return 0

	def determin_status(self):
		status = 1
		if self.state.time > self.data.time_to_finish * 10 ** 6:
			status = 0
		if not self.state.dest_hit:
			status = 0
		if sum(self.state.circles_hit) != len(self.state.circles_hit):
			status = 0
		if sum(self.state.rects_hit) > 0:
			status = 0
		return status

	def start_stop_thread(self, t):
		self.stop_thread = threading.Thread(target=self.stop_tracking, args=(t,))
		self.stop_thread.start()	

	def stop_tracking(self, t):
		self.is_running = False
		print("Tracking stopped!")
		self.data.state.time = t
		self.state.success_status = self.determin_status()

		if self.reading_thread.is_alive():
			self.reading_thread.join()  # Wait for reading thread to finish
		if self.processing_thread.is_alive():
			self.processing_thread.join() 
		if self.drawing_thread.is_alive():
			self.drawing_thread.join() 

		self.path_color = SUCCESS_PATH_COLOR if self.state.success_status else FAILURE_PATH_COLOR
		if self.state.success_status:
			self.success_beep_thread.start()
		else:
			self.failure_beep_thread.start()

		self.show_path_flag = True
		self.update()

		QTimer.singleShot(1500, self.manager.next_test)
  
		self.save_data()
  
	def move_rects(self):
		
		# last_sample_time = self.start_time
		# while self.is_running or self.start_time is None:
			# current_time = time.perf_counter_ns()
			# if current_time - last_sample_time >= 1 * 10 ** 6:
			# 	last_sample_time = current_time
				
				# for rect in self.data.rects:
				# 	rect.update_pos(self.data.dimensions)
				# self.update()
				# time.sleep(0.001)
		pass

	def calc_output_path(self):
		directory_path = Path(self.target_dir)
		full_path = directory_path / f'{self.manager.test_number}.csv'
		return full_path

	def generate_header_and_first_row(self):
		header = ['x', 'y', 'pressure', 'time', 'total_test_time', 'success', 'time_out', 'source_hit', 'dest_hit']
		first_row = [*self.state.points[0], self.state.time / 10**6, self.state.success_status, int(self.state.time > self.data.time_to_finish*10**6), self.state.source_hit, self.state.dest_hit, *self.state.circles_hit, *self.state.rects_hit]
		for i in range(len(self.state.circles_hit)):
			header += [f'circle_{i+1}_hit']
		for i in range(len(self.state.rects_hit)):
			header += [f'rect_{i+1}_hit']
		return header, first_row

	def save_data(self):
		file_path = self.calc_output_path()
	
		with file_path.open(mode='w', newline='') as csv_file:
			writer = csv.writer(csv_file)

			# Write the header row
			header, first_row = self.generate_header_and_first_row()
			writer.writerow(header)
			writer.writerow(first_row)

			# Write the rows from the data list
			for row in self.state.points[1:]:
				writer.writerow(row)
		self.save_diffs()


	def calc_output_diff_path(self):
		directory_path = Path(self.target_dir)
		full_path = directory_path / f'{self.manager.test_number}_diffs.txt'
		return full_path

	def save_diffs(self):
		file_path = self.calc_output_diff_path()
	
		with file_path.open(mode='w', newline='') as file:
			for i in range(1, len(self.state.points)):
				file.write(f"{self.state.points[i][3] - self.state.points[i-1][3]}\n")


	def paintEvent(self, event):
		painter = QPainter(self)
		painter.fillRect(self.rect(), QColor(*BACKGROUND_COLOR))

		self.data.source_circle.draw(painter)
		self.data.dest_circle.draw(painter)
		for circle in self.data.middle_circles:
			circle.draw(painter)
		for rect in self.data.rects:
			rect.draw(painter)

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

