from PyQt6.QtWidgets import QApplication
from config import OFFSET_FROM_DEST_CM


class TesterInformation:
	def __init__(self, name, lastname, phone_number, age, dominant_hand, vision, test_type, additional_info):
		self.name = name
		self.lastname = lastname
		self.phone_number = phone_number
		self.age = age
		self.dominant_hand = dominant_hand
		self.vision = vision
		self.test_type = test_type
		self.additional_info = additional_info


class ScreenDimensions:
	def __init__(self, app: QApplication):
		screen = app.primaryScreen()
	
		screen_resolution = screen.geometry()
		self.WINDOW_WIDTH_PIXELS = screen_resolution.width()
		self.WINDOW_HEIGHT_PIXELS = screen_resolution.height() 

		physical_size_mm = screen.physicalSize()  
		self.WINDOW_WIDTH_CM = physical_size_mm.width() / 10
		self.WINDOW_HEIGHT_CM = physical_size_mm.height() / 10

		self.X_CM_TO_PIXEL = self.WINDOW_WIDTH_PIXELS / self.WINDOW_WIDTH_CM
		self.Y_CM_TO_PIXEL = self.WINDOW_HEIGHT_PIXELS / self.WINDOW_HEIGHT_CM
		self.X_PIXEL_TO_CM = self.WINDOW_WIDTH_CM / self.WINDOW_WIDTH_PIXELS
		self.Y_PIXEL_TO_CM = self.WINDOW_HEIGHT_CM / self.WINDOW_HEIGHT_PIXELS


class Data:
	def __init__(self, time_to_finish, rate, source, dest, circles, rects, passing_offset=OFFSET_FROM_DEST_CM):
		self.dimensions = ScreenDimensions(QApplication.instance())
		self.source_circle = self.process_input_circle_data(source)
		self.dest_circle = self.process_input_circle_data(dest)
		self.middle_circles = [self.process_input_circle_data(circle) for circle in circles]
		self.rects = [self.process_input_rect_data(rect) for rect in rects]
		self.time_to_finish = time_to_finish
		self.rate = rate
		self.passing_offset = passing_offset

		self.state = State(self)
	

	def process_input_circle_data(self, circle):
		x, y, r = circle
		x *= self.dimensions.X_CM_TO_PIXEL
		y *= self.dimensions.Y_CM_TO_PIXEL
		rx = r * self.dimensions.X_CM_TO_PIXEL
		ry = r * self.dimensions.Y_CM_TO_PIXEL  
		return (x, y, rx, ry)


	def process_input_rect_data(self, rect):
		x, y, w, h = rect
		x *= self.dimensions.X_CM_TO_PIXEL
		y *= self.dimensions.Y_CM_TO_PIXEL
		w *= self.dimensions.X_CM_TO_PIXEL
		h *= self.dimensions.Y_CM_TO_PIXEL
		return (x, y, w, h)


	def process_new_point(self, x, y, p, t):
		self.state.points.append((x, y, p, t))

		# check collusions
		sx, sy, srx, sry = self.source_circle
		if abs(sx - x) <= srx and abs(sy - y) <= sry:
			self.state.source_hit = 1
		
		dx, dy, drx, dry = self.dest_circle
		if abs(dx - x) <= drx and abs(dy - y) <= dry:
			self.state.dest_hit = 1
		
		for i in range(len(self.middle_circles)):
			cx, cy, crx, cry = self.middle_circles[i]
			if abs(cx - x) <= crx and abs(cy - y) <= cry:
				self.state.circles_hit[i] = 1

		for i in range(len(self.rects)):
			rx, ry, rw, rh = self.rects[i]
			if x <= rx+rw and x >= rx and y <= ry+rh and y >= ry:
				self.state.rects_hit[i] = 1 


	def to_dict(self):
		return {
			"time": self.time_to_finish,
			"rate": self.rate,
			"source": self.source_circle,
			"dest": self.dest_circle,
			"circles": self.middle_circles,
			"rects": self.rects,
		}


class State: 
	def __init__(self, data:Data):
		self.source_hit = 0
		self.dest_hit = 0
		self.circles_hit = [0] * len(data.middle_circles)
		self.rects_hit = [0] * len(data.rects)
		
		self.time = None
		self.points = []
		self.success_status = 0






