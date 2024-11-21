import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from pages import PageManager, FormPage, TestPage
from models import ScreenDimensions

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.dimensions = ScreenDimensions(QApplication.instance())		
		self.setWindowTitle("Page Transition Example")
		self.setGeometry(0, 0, self.dimensions.WINDOW_WIDTH_PIXELS, self.dimensions.WINDOW_HEIGHT_PIXELS)

		# Initialize PageManager
		self.manager = PageManager('./test_input.csv')

		# Connect PageManager signals to transition handler
		self.manager.start_test_signal.connect(self.show_test_page)
		self.manager.finished_signal.connect(self.on_tests_complete)

		# The directory where results are stored
		self.target_dir = None
		
		# Start with the FormPage
		self.show_form_page()

	def show_form_page(self):
		"""Display the form page."""
		form_page = FormPage(self, self.manager)
		self.set_central_widget(form_page)

	def show_test_page(self, data):
		"""Display a test page."""
		test_page = TestPage(data, self.target_dir, self.manager)
		self.set_central_widget(test_page)

	def on_tests_complete(self):
		"""Handle when all tests are completed."""
		print("All tests completed!")
		self.close()  # Exit application or show a "Finished" page

	def set_central_widget(self, widget):
		"""Utility to replace the central widget."""
		if self.centralWidget():
			self.centralWidget().deleteLater()  # Clean up the old widget
		self.setCentralWidget(widget)


def main():
	app = QApplication(sys.argv)
	main_window = MainWindow()
	main_window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
