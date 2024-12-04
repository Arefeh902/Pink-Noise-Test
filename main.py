import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from models import Data, ScreenDimensions
from config import INPUT_FILE_PATH
from pages.form_page import FormPage
from pages.test_page import TestPage, PageManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize screen dimensions
        self.dimensions = ScreenDimensions(QApplication.instance())
        self.setWindowTitle("Main Window")
        self.setGeometry(0, 0, self.dimensions.WINDOW_WIDTH_PIXELS, self.dimensions.WINDOW_HEIGHT_PIXELS)

        # Initialize PageManager for navigation and logic
        self.manager = PageManager(INPUT_FILE_PATH)
        self.manager.start_test_signal.connect(self.show_test_page)
        self.manager.finished_signal.connect(self.on_tests_complete)

        # Directory to store results
        self.target_dir: str | None = None

        # Display the initial FormPage
        self.show_form_page()

    def show_form_page(self) -> None:
        """Display the form page."""
        form_page = FormPage(self, self.manager)
        self.set_central_widget(form_page)

    def show_test_page(self, data: Data) -> None:
        """Display the test page with the given data."""
        test_page = TestPage(data, self.target_dir, self.manager)
        self.set_central_widget(test_page)

    def on_tests_complete(self) -> None:
        """Handle actions when all tests are completed."""
        print("All tests completed!")
        # Placeholder for any further actions, e.g., showing a summary or saving results
        self.close()

    def set_central_widget(self, widget: QWidget) -> None:
        """Safely replace the central widget."""
        if (current_widget := self.centralWidget()) is not None:
            current_widget.deleteLater()  # Clean up the old widget
        self.setCentralWidget(widget)


def main() -> None:
    """Main entry point of the application."""
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
