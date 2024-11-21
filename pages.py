import time
from PyQt6.QtWidgets import (
QApplication, QWidget, QLabel, QLineEdit, QComboBox, QSpinBox,
QRadioButton, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QButtonGroup
)
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import QTimer, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import QCursor, QTabletEvent
from models import Data, State, ScreenDimensions
from config import BACKGROUND_COLOR, SOURCE_CIRCLE_COLOR, MIDDLE_CIRCLE_COLOR, DESTINATION_CIRCLE_COLOR, RECT_COLOR
import sys
from config import DELAY_BETWEEN_TESTS
import pysine
import csv
from pathlib import Path

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
		rectangle_size = 4
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
				print('='*40)
				print(row)
				yield self.get_data_from_input_row(row)


	def start_tests(self):
		self.next_test()

	def next_test(self):
		try:
			data = next(self.data_generator)
			self.start_test_signal.emit(data, )  # Emit signal to create a TestPage
		except StopIteration:
			print("All tests completed!")
			self.finished_signal.emit()



######################################################################################
#                                                                                    #
#                                   TEST Page                                        #
#                                                                                    #  
######################################################################################
from config import (
	SUCCESS_PATH_COLOR, FAILURE_PATH_COLOR,
	START_FREQUENCY, START_DURATION_MS,
	SUCCESS_FREQUENCY, SUCCESS_DURATION_MS,
	FAILURE_FREQUENCY, FAILURE_DURATION_MS
	)

class TestPage(QWidget):
	def __init__(self, data:Data, target_dir:str, manager: PageManager=None):
		super().__init__()
		
		print('in testpage init')
		self.data = data
		self.state = self.data.state
		self.target_dir = target_dir
		print(self.target_dir)
		self.manager = manager
		self.setWindowTitle("Circles Display")
		self.setGeometry(0, 0, data.dimensions.WINDOW_WIDTH_PIXELS, data.dimensions.WINDOW_HEIGHT_PIXELS)
		

		self.input_timer = QTimer(self)  # Timer for sampling mouse position
		self.input_timer.timeout.connect(self.read_postions)
		self.sampling_rate_ms = max(1000 // self.data.rate, 1) # Set sampling rate in milliseconds
		
		self.tablet_x = None
		self.tablet_y = None
		self.tablet_p = None
		self.tablet_connected = False
		self.start_time = None

		self.show_path_flag = False 
		self.path_color = FAILURE_PATH_COLOR


	# def tabletEvent(self, event: QTabletEvent):
	# 	# print(event.type())
	# 	print('='*30)
	# 	if event.type() == QEvent.Type.TabletPress:
	# 		print("Tablet Press")
		
	# 	# pos = event.position()
	# 	# self.tablet_x = pos.x()
	# 	# self.tablet_y = pos.y()
	# 	# self.table_p = event.pressure()
		
	# 	# if event.type() == QTabletEvent.TabletEventType.TabletPress and self.start_time is None:
	# 	# 	self.on_tracking_start()
		
	# 	# self.tablet_connected = True
	# 	# print("tablet connected!")
		
	# 	self.tablet_x = event.position().x()
	# 	self.tablet_y = event.position().y()
	# 	self.tablet_p = event.pressure()
		
	# 	event.accept()


	def mousePressEvent(self, event):
		if self.tablet_connected:
			return
		if self.tablet_connected is False and self.start_time is None:
			self.on_tracking_start()


	def read_postions(self):
		current_x = None
		current_y = None
		current_p = None

		if self.tablet_connected:
			current_x = self.tablet_x
			current_y = self.tablet_y
			current_p = self.tablet_p
		else:
			global_mouse_pos = QCursor.pos()  # Get global position
			widget_mouse_pos = self.mapFromGlobal(global_mouse_pos)
			current_x, current_y = widget_mouse_pos.x(), widget_mouse_pos.y()

		elapsed_time = (time.perf_counter_ns()  - self.start_time)
		self.data.process_new_point(current_x, current_y, current_p, elapsed_time)

		# check for complition
		dx, dy, drx, dry = self.data.dest_circle
		if elapsed_time >= self.data.time_to_finish * 10 ** 6:
			self.on_tracking_stop(elapsed_time)
		elif self.data.state.dest_hit:
			self.on_tracking_stop(elapsed_time)
		elif current_x - (dx + drx) >= self.data.passing_offset * self.data.dimensions.X_CM_TO_PIXEL: 
			self.on_tracking_stop(elapsed_time)

	def determin_status(self):
		status = 1
		if self.state.time > self.data.time_to_finish * 10 ** 6:
			print('time!')
			status = 0
		if not self.state.dest_hit:
			print('no hit')
			status = 0
		if sum(self.state.circles_hit) != len(self.state.circles_hit):
			print('missed circle')
			status = 0
		if sum(self.state.rects_hit) > 0:
			print()
			status = 0
		return status

	def on_tracking_start(self):
		self.start_time = time.perf_counter_ns()
		self.input_timer.start(self.sampling_rate_ms)
		pysine.sine(frequency=START_FREQUENCY, duration=START_DURATION_MS) 
		print('timer started!')

	def on_tracking_stop(self, elapsed_time):
		print('stop!')
		self.data.state.time = elapsed_time 
		self.state.success_status = self.determin_status()
		self.input_timer.stop()

		# show path
		if self.state.success_status:
			self.path_color = SUCCESS_PATH_COLOR

		self.show_path_flag = True
		self.update()

		if self.state.success_status:
			pysine.sine(frequency=SUCCESS_FREQUENCY, duration=SUCCESS_DURATION_MS) 
		else:
			pysine.sine(frequency=FAILURE_FREQUENCY, duration=FAILURE_DURATION_MS) 

		QTimer.singleShot(1500, self.trigger_next_test)
		self.save_data()


	def calc_output_path(self):
		# Ensure the directory is a Path object
		directory_path = Path(self.target_dir)
		# Join the file name to the directory
		full_path = directory_path / f'{self.manager.test_number}.csv'
		return full_path

	def generate_header_and_first_row(self):
		header = ['x', 'y', 'pressure', 'time', 'total_test_time', 'success', 'source_hit', 'dest_hit']
		first_row = [*self.state.points[0], self.state.time, self.state.success_status, self.state.source_hit, self.state.dest_hit, *self.state.circles_hit, *self.state.rects_hit]
		for i in range(len(self.state.circles_hit)):
			header += [f'circle_{i+1}_hit']
		for i in range(len(self.state.rects_hit)):
			header += [f'rect_{i+1}_hit']
		return header, first_row


	def save_data(self):
		file_path = self.calc_output_path()
		print(file_path)
	
		with file_path.open(mode='w', newline='') as csv_file:
			writer = csv.writer(csv_file)

			# Write the header row
			header, first_row = self.generate_header_and_first_row()
			writer.writerow(header)
			writer.writerow(first_row)

			# Write the rows from the data list
			for row in self.state.points[1:]:
				writer.writerow(row)



	def trigger_next_test(self):
		self.manager.next_test()


	def drawCircle(self, painter, circle, color):
		x, y, rx, ry = circle
		x -= rx; y -= ry
		painter.setPen(QPen(QColor(0,0,0)))
		painter.setBrush(QColor(*color))  # Fill color
		painter.drawEllipse(int(x), int(y), int(rx * 2), int(ry * 2))


	def paintEvent(self, event):
		# print('in paint!')
		painter = QPainter(self)
		painter.fillRect(self.rect(), QColor(*BACKGROUND_COLOR))

		# draw source
		self.drawCircle(painter, self.data.source_circle, SOURCE_CIRCLE_COLOR)
  
		# draw dest
		self.drawCircle(painter, self.data.dest_circle, DESTINATION_CIRCLE_COLOR)
		
		# draw middle circles
		for circle in self.data.middle_circles:
			self.drawCircle(painter, circle, MIDDLE_CIRCLE_COLOR)

		# draw rectangles
		for x, y, w, h in self.data.rects:
			painter.setBrush(QColor(*RECT_COLOR))
			painter.drawRect(int(x), int(y), int(w), int(h))
		
		if self.show_path_flag:
			pen = QPen(QColor(*self.path_color), 2)
			painter.setPen(pen)
			for i in range(len(self.data.state.points) - 1):
				painter.drawLine(
				int(self.data.state.points[i][0]), int(self.data.state.points[i][1]),
				int(self.data.state.points[i + 1][0]), int(self.data.state.points[i + 1][1])
				)


######################################################################################
#                                                                                    #
#                                   FORM Page                                        #
#                                                                                    #
######################################################################################

class FormPage(QWidget):
	def __init__(self, main_window, test_manager: PageManager):
		super().__init__()
		self.main_window = main_window
		self.dimensions = main_window.dimensions
		self.test_manager = test_manager
		self.setWindowTitle("Form Page")
		self.setGeometry(0, 0, self.dimensions.WINDOW_WIDTH_PIXELS, self.dimensions.WINDOW_HEIGHT_PIXELS)

		# Create form fields
		self.name_input = QLineEdit()
		self.last_name_input = QLineEdit()
		self.phone_input = QLineEdit()
		self.age_input = QSpinBox()
		self.age_input.setRange(1, 120)

		# Dominant hand selection
		self.hand_group = QButtonGroup()
		self.right_hand = QRadioButton("Right Hand")
		self.left_hand = QRadioButton("Left Hand")
		self.hand_group.addButton(self.right_hand)
		self.hand_group.addButton(self.left_hand)

		# Normal or corrected vision
		self.vision_combo = QComboBox()
		self.vision_combo.addItems(["Normal", "Corrected (Glasses)"])

		# Test type selection
		self.test_type_combo = QComboBox()
		self.test_type_combo.addItems(["Type 1", "Type 2", "Type 3"])

		# Additional information
		self.additional_info = QTextEdit()

		# Submit button
		self.submit_button = QPushButton("Submit")
		self.submit_button.clicked.connect(self.submit_form)

		# Layout setup
		self.setup_layout()

	def setup_layout(self):
		main_layout = QVBoxLayout()
		main_layout.setContentsMargins(20, 20, 20, 20)  # Set margins for the whole form
		main_layout.setSpacing(10)  # Add spacing between form sections

		# Set fixed width for input fields
		self.name_input.setFixedWidth(200)
		self.last_name_input.setFixedWidth(200)
		self.phone_input.setFixedWidth(200)
		self.age_input.setFixedWidth(100)
		self.vision_combo.setFixedWidth(200)
		self.test_type_combo.setFixedWidth(200)

		# Name fields
		main_layout.addLayout(self.create_row("First Name   :", self.name_input))
		main_layout.addLayout(self.create_row("Last Name:", self.last_name_input))

		# Phone number
		main_layout.addLayout(self.create_row("Phone Number :", self.phone_input))

		# Age
		main_layout.addLayout(self.create_row("Age  :", self.age_input))

		# Dominant hand
		hand_layout = QHBoxLayout()
		hand_layout.addWidget(QLabel("Dominant Hand:"))
		hand_layout.addWidget(self.right_hand)
		hand_layout.addWidget(self.left_hand)
		hand_group_box = QGroupBox()
		hand_group_box.setLayout(hand_layout)
		main_layout.addWidget(hand_group_box)

		# Vision
		main_layout.addLayout(self.create_row("Vision:", self.vision_combo))

		# Test type
		main_layout.addLayout(self.create_row("Test Type :", self.test_type_combo))

		# Additional information
		main_layout.addWidget(QLabel("Additional Information:"))
		main_layout.addWidget(self.additional_info)

		# Submit button
		main_layout.addWidget(self.submit_button)

		self.setLayout(main_layout)

	def create_row(self, label_text, widget):
		"""Helper method to create a horizontal row for label and input."""
		row_layout = QHBoxLayout()
		row_layout.setSpacing(10)  # Spacing between label and input
		row_layout.addWidget(QLabel(label_text))
		row_layout.addWidget(widget)
		row_layout.addStretch() 
		return row_layout

	def submit_form(self):
		# Gather data from the form
		name = self.name_input.text()
		last_name = self.last_name_input.text()
		phone_number = self.phone_input.text()
		age = self.age_input.value()
		dominant_hand = "Right Hand" if self.right_hand.isChecked() else "Left Hand" if self.left_hand.isChecked() else "Unspecified"
		vision = self.vision_combo.currentText()
		test_type = self.test_type_combo.currentText()
		additional_info = self.additional_info.toPlainText()

		# Ensure the base directory exists
		from config import OUTPUT_DIR
		from pathlib import Path

		base_path = Path(OUTPUT_DIR)
		# Construct the target directory name based on form input
		target_name = f"{name}_{last_name}_{phone_number}"  # Example: "JohnDoe_Test1"
		target_dir = base_path / target_name

		print(str(target_dir))
		if not target_dir.exists():
			print(f"Base directory '{target_dir}' does not exist. Creating it...")
			target_dir.mkdir(parents=True)



		self.main_window.target_dir = str(target_dir)

		# create base info file
		file_name = 'info.txt'
		file_path = target_dir / file_name

		# Create a list of lines to write to the file
		lines = [
			f"Name: {name}",
			f"Last Name: {last_name}",
			f"Phone Number: {phone_number}",
			f"Age: {age}",
			f"Dominant Hand: {dominant_hand}",
			f"Vision: {vision}",
			f"Test Type: {test_type}",
			f"Additional Info: {additional_info}",
		]

		# Write to the file
		with open(file_path, "w") as file:
			file.write("\n".join(lines))

		# # Write the form data to the file
		# with file_path.open("w") as file:
		# 	for key, value in form_data.items():
		# 		file.write(f"{key}: {value}\n")

		# call the function for reading input files and stuff!
		self.test_manager.start_tests()
