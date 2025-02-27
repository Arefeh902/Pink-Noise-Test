from PyQt6.QtWidgets import QApplication
from config import OFFSET_FROM_DEST_CM, SOURCE_CIRCLE_COLOR, DESTINATION_CIRCLE_COLOR, MIDDLE_CIRCLE_COLOR
from shapes import Circle, Rectangle
from config import ORIGIN_X, ORIGIN_Y

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


class TabletData:
    def __init__(self, x, y, pressure, x_tilt, y_tilt, rotation, time):
        self.x = x
        self.y = y
        self.pressure = pressure
        self.x_tilt = x_tilt
        self.y_tilt = y_tilt
        self.rotation = rotation
        self.time = time
    
    def return_data(self):
        return (self.x, self.y, self.pressure, self.x_tilt, self.y_tilt, self.rotation, self.time)

    def copy(self):
        return TabletData(self.x, self.y, self.pressure, self.x_tilt, self.y_tilt, self.rotation, self.time)

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
    def __init__(self, time_to_finish, rate, source, dest, circles, rects, y_offset_change_pixels=75, passing_offset=OFFSET_FROM_DEST_CM):
        self.dimensions = ScreenDimensions(QApplication.instance())
        self.dimensions.WINDOW_HEIGHT_PIXELS -= y_offset_change_pixels
        self.dimensions.WINDOW_HEIGHT_CM = self.dimensions.WINDOW_HEIGHT_PIXELS * self.dimensions.Y_PIXEL_TO_CM
        
        self.source_circle = self.process_input_circle_data(source, SOURCE_CIRCLE_COLOR)
        self.dest_circle = self.process_input_circle_data(dest, DESTINATION_CIRCLE_COLOR)
        self.middle_circles = [self.process_input_circle_data(circle, MIDDLE_CIRCLE_COLOR) for circle in circles]
        self.rects = [self.process_input_rect_data(rect) for rect in rects]
        self.time_to_finish = time_to_finish
        self.rate = rate
        self.passing_offset = passing_offset

        self.state = State(self)
    
    def process_x_and_y(self, x, y):
        y = (self.dimensions.WINDOW_HEIGHT_PIXELS - ORIGIN_Y*self.dimensions.Y_CM_TO_PIXEL) - y
        x = ORIGIN_X * self.dimensions.X_CM_TO_PIXEL + x
        return x, y

    def reverse_process_x_and_y(self, x, y):
        y = (self.dimensions.WINDOW_HEIGHT_CM - ORIGIN_Y)*self.dimensions.Y_CM_TO_PIXEL - y
        x = - (ORIGIN_X * self.dimensions.X_CM_TO_PIXEL) + x
        return x, y

    def process_x_and_y_for_record(self, x, y):
        x, y = self.reverse_process_x_and_y(x, y)
        x *= self.dimensions.X_PIXEL_TO_CM * 10
        y *= self.dimensions.Y_PIXEL_TO_CM * 10
        return x, y

    def reverse_process_x_and_y_for_record(self, x, y):
        x *= self.dimensions.X_CM_TO_PIXEL / 10
        y *= self.dimensions.Y_CM_TO_PIXEL / 10
        x, y = self.process_x_and_y(x, y)
        return x, y

    def process_input_circle_data(self, circle, color):
        x, y, r = circle
        x *= self.dimensions.X_CM_TO_PIXEL
        y *= self.dimensions.Y_CM_TO_PIXEL
        x, y = self.process_x_and_y(x, y)
        rx = r * self.dimensions.X_CM_TO_PIXEL
        ry = r * self.dimensions.Y_CM_TO_PIXEL
        return Circle(x, y, rx, ry, color)


    def process_input_rect_data(self, rect):
        x, y, w, h = rect
        x *= self.dimensions.X_CM_TO_PIXEL
        y *= self.dimensions.Y_CM_TO_PIXEL
        x, y = self.process_x_and_y(x, y)
        w *= self.dimensions.X_CM_TO_PIXEL
        h *= self.dimensions.Y_CM_TO_PIXEL
        return Rectangle(x, y, w, h)


    def process_input_data(self, tablet_data, t):
        x, y = tablet_data[0], tablet_data[1]

        # check collusions
        self.state.source_hit |= self.source_circle.check_hit(x, y)
        self.state.dest_hit |= self.dest_circle.check_hit(x, y)
        if not self.state.dest_hit and len(self.state.points) > 1:
            self.dest_circle.check_hit_line_segment(x, y, *self.state.points[-1][:2])
        
        for i in range(len(self.middle_circles)):
            self.state.circles_hit[i] |= self.middle_circles[i].check_hit(x, y)
            if not self.state.circles_hit[i] and len(self.state.points) > 1:
                self.state.circles_hit[i] |= self.middle_circles[i].check_hit_line_segment(x, y, *self.reverse_process_x_and_y_for_record(*self.state.points[-1][:2]))

        for i in range(len(self.rects)):
            self.state.rects_hit[i] |= self.rects[i].check_hit(x, y) 
            if not self.state.rects_hit[i] and len(self.state.points) > 1:
                self.state.rects_hit[i] |= self.rects[i].check_hit_line_segments(x, y, *self.reverse_process_x_and_y_for_record(*self.state.points[-1][:2]))
                pass

        tablet_data[0], tablet_data[1] = self.process_x_and_y_for_record(x, y)
        self.state.points.append((*tablet_data, t))


class State: 
    def __init__(self, data:Data):
        self.source_hit = 0
        self.dest_hit = 0
        self.circles_hit = [0] * len(data.middle_circles)
        self.rects_hit = [0] * len(data.rects)
        
        self.time = None
        self.points = []
        self.dest_passed = 0
        self.success_status = 0






