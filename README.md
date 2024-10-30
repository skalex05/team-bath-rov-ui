# Team Bath Hydrobotics ROV UI

## Code Standards

Python code should be written to adhere to the [PEP 8 Standard](..%2F..%2F..%2FAppData%2FLocal%2FTemp%2FPEP%208-%20The%20Style%20Guide%20for%20Python%20Code.url) for laying out code to help maintain clear code readability.

Make comments where neccessary to help produce self documenting code!

Type hints should be used where appropriate. This can greatly help with development and debugging; Tools like IntelliJ can use these for providing more accurate code suggestions.

**Do not** overuse comments/use comments to explain trivial tasks.


Use [QT Creator](https://doc.qt.io/qtcreator/creator-how-to-install.html) for designing the layout of the UI, stored in `*.ui` files.

Any code editor should work fine during development; ideally one which aligns with PEP 8.


## Design Overview

Refer frequently to design resources to ensure implementations are fit for purpose. 

User experience and simplicity are crucial aspects of the design.

The system will be used in a time sensitive environment and thus it is important that it is responsive and requires minimal input from the user.

Additionally, the competition strains safety and risk mitigation with the design of our system. This should be reflected within the UI as well as the ROV itself.

Ensuring that the UI is designed to be fault tolerant and gracefully handle unexpected scenarios is essential.

More information can be found below:

[Figma Design](https://www.figma.com/design/CVX1dHaXI9s1b6nb9SfE9z/Team-Bath-Hydrobotics?node-id=0-1&t=LOLOn3gkAG4KWGFB-0)

[User Stories](https://computingservices.sharepoint.com/:w:/r/sites/TeamBathRobotics/Shared%20Documents/Resources/Autonomy%20%26%20Interface%20Team/User%20Interface/Concept%20Designs/User%20Stories.docx?d=wa64ea7a6307a4422a6f4c1185b1a4e85&csf=1&web=1&e=2pIOby)

This README will serve as a document for defining specific code implementations in QT.

## Development Process

Create your own branch of this repo which you can use to push changes to.
Install all dependencies to the project by running the following in the project directory:

`pip install -r requirements.txt`

Code can either be run in your code editor or from QT Creator by running `main.py`.

The project directory for your chosen editor should be within the `/source` folder.

**Note**: QT Creator may require you to specify a run configuration in which case yours should look like the following:

The script attribute should refer to `main.py`
![](README-IMAGES/qtcreatorrunsetup.png)

# Implementation

## App Object

The app object inherits from `QApplication` and is used to contain everything related to the UI.

Information pertaining to the current state of the UI should be stored here so that it is globally visible to different widgets in the application.

Other widget objects should contain an attribute referencing to this app object so that they can retrieve shared program information.

**The app stores information including:**

- Tasks
- Timer
- References to each `Window` Widget
- Reference to the `Dock` Widget
- Information about processes that send "dummy" data to the UI (Temporary)

**Signals:**

- `task_checked` - Raised when a checkbox in the list of tasks is changed.
- `camera_initialisation_complete` - Raised when a camera is successfully initialised.

**Methods:**

- `close()` - Closes all windows associated with the application, joins all external threads, closes all associated processes.
- `init_data_interface(redirect_stdout, redirect_stderr)` - Starts the `DataInterface` object in a new thread and sets a reference in each window to this object, so they can access it.
- `reset_task_completion()` - Sets all the tasks to incomplete.

## Task Object

This object inherits `QWidget` and is used to store information about a particular task. This includes a title, description and time when the user should start this task. The `Task` loads a template widget from `task_widget.ui` which contains a checkbox and label for the `start_time`.

**Methods:**

- `set_attr_(key, value)` - Overwritten to update widgets if the `Task`'s attributes are changed.
- `on_check()` - Called when the checkbox is checked/unchecked. This changes the complete attribute and emits `App`'s `Task_Checked` signal.

## DataInterface Object

The `DataInterface` is used to store the current state of the ROV/Float, stdout from the UI and from the ROV and ROV video streams.
This object centrally manages multiple threads, which are each responsible of processing data from a socket connection. 
Each thread will **emit** a different **signal** when new data is recieved/connction is lost.
Each thread will connect to its own **socket** with a unique **port** number.

A **socket** may be of type `SOCK_STREAM` which uses **TCP** to transfer data. Use this when it is neccessary **all** data should be recieved.
A **socket** may insteda use type `SOCK_DGRAM` which uses **UDP**. Use this where packet loss is acceptable and not all data needs to be recieved.

- `ROV Data Thread` - Emits `rov_data_update` - **Port 52525** - `SOCK_DGRAM`
- `Float Data Thread` - Emits `float_data_update` - **Port 52526** - `SOCK_DGRAM`
- `Video Stream Thread`(s - One for each video stream) - SOCKETS NOT YET IMPLEMENTED
- `Stdout Thread` - SOCKET NOT YET IMPLEMENTED

**Signals:**

These sockets can be connceted to by windows if they are supposed to display information from `DataInterface`

- `rov_data_update()`
- `float_data_update()`
- `video_stream_update()`
- `stdout_update()`

**Methods:**

Each Thread has it's own function that it runs which are contained inside this class:

- `f_rov_data_thread()` - Updates `DataInterface` attributes to the values to the newest `ROVData`recieved.
- `f_float_data_thread()` - Updates `DataInterface` attributes to the values to the newest `FloatData`recieved.
- `f_video_stream_thread()` - Calls `update_camera_frame()` for each `VideoStream`
- `f_stdout_thread()` - Currently just moves stdout from a redirected output buffer into another buffer that is consumed by the `Copilot` window to display new stdout.

- `close()`

## ROVData

This is a **pickleable** object containing metrics from the ROV which are sent across a socket to be recieved by the UI process.

Attribute names in `ROVData` must match exactly to a corresponding attibute in `DataInterface`.

**Attributes:**

- `attitude`
- `angular_acceleration`
- `angular_velocity`
- `acceleration`
- `velocity`
- `depth`
- `ambient_temperature`
- `ambient_pressure`
- `internal_temperature `

- `main_sonar`
- `FL_sonar`
- `FR_sonar`
- `BR_sonar`
- `BL_sonar`

- `actuator_1`
- `actuator_2`
- `actuator_3`
- `actuator_4`
- `actuator_5`
- `actuator_6`

## FloatData

This is a **pickleable** object containing metrics from the Float which are sent across a socket to be recieved by the UI process.

Attribute names in `FloatData` must match exactly to a corresponding attibute in `DataInterface`.

**Attributes:**

- `float_depth`

## VideoStream Object

*Note:*

*Some of this code may need to be altered/moved to the ROV itself when video feed is received from the ROV rather than from local webcams.*

****

This is used to store information related to the camera feeds on the ROV.

The key argument of this object is the `camera_frame` which stores a **numpy**-style 2D array of pixels of what the video feed is currently receiving.
This is not to be confused with `camera_feed` which is a `cv2.VideoCapture` object to read frames from.

**Methods:**

- `start_init_camera_feed()` - This creates a thread which runs `init_camera_feed()`
- `init_camera_feed()` - This function attempts to read a frame from the `camera_feed`. If it is successful, it will **emit** the `camera_initialised` signal in the `App` object. Otherwise, it will attempt several more times by recursively calling the function until a maximum number of attempts is reached. At which point, the user must press the `Reinitialise Cameras` action to restart this process. 
- `update_camera_frame()` - The data in `camera_frame` is updated with the newest data read from `camera_feed` *(Note: Testing is needed to see what happens when an initialised camera feed suddenly becomes unavailable. Program should identify and deal with this gracefully beyond just flooding the console with "Could not read...")*
- `generate_pixmap(target_width, target_height)` - translates the `camera_frame` into a `QPixmap` object of a desired size. Aspect ratio of the image is maintained.
## Window Widget

Each window is a frameless, full screen window (1920x1080) that can be moved around to different monitors using the `NavBar` at the top of the screen.

The `Window` class is a subclasses of `QFrame`s and is a container for all UI content within a window. 
The `Window` class should not be used directly but only through the subclasses `Pilot`,`Copilot` and`Grapher`. 
Each window should load all static widgets through a `.ui` of the same name. 

Widgets inside a window can be referenced like so:

![](README-IMAGES/widgetreferencing.png)

Including type hints here makes development much easier.

The `__init__` method takes three arguments:

- file - The `*.ui` file to be loaded into the window.
- app - The `App` parent to this window. The window can reference this to get global data.
- monitor - A `Monitor` object from the `screeninfo` library. This is used to determine which monitor the window should appear on at launch.

**Methods:**

- `attach_nav_bar()` - Used on startup by the `App` object to build the window's `NavBar`
- `attach_data_interface()` - Should be overridden by subclasses if their window requires connecting to `DataInterface` signals.
- `close_event()` - Triggered by the window closing. If a window closes, so should the entire app.

## Dock Widget

The `Dock` widget inherits from `QStackedWidget` and allows multiple `Window` objects to be stacked ontop of each other if there are not enough displays available.
See the section on the `NavBar` widget as that is used in conjunction with the `Dock` to allow the user to switch between the different windows in the stack.

Whenever a widget is added(docked) or removed(undocked), `on_dock_change()` is called.

When `Window` at the top of the stack changes, the `WindowTitle` propertty of the `Dock` is changed.

**Methods:**

- `add_windows(*windows)` - adds windows to the stack. Calls `on_dock_change()`
- `on_dock_change()` - rebuilds the `NavBar` for each `Window` in the stack.
- `close_event()` - triggered the window is closing. If a window closes, so should the entire app.

## NavBar Widget

Each window has a custom navigation bar at the top of the screen to override the default one provided by Windows.

It provides functionality for **moving a window to a different screen**, **minimising** and **closing** windows and **docking/undocking** windows.
For docked windows, the navbar will list all other docked windows that the user can switch to and view.

**Methods:**

- `generate_layout()` - Creates `QPushButton`s for each standard button and `NavWindowButton`s for each docked window. These are displayed on the `NavBar`.
- `clear_layout(layout)` - Removes all of the `QPushButton`s from the `NavBar` layout.
- `minimise()` - minimises the `Dock` if the parent `Window` is *docked* and minimises the parent `Window` itself if it is *undocked*.
- `f_dock()` - adds the parent `Window` to the `Dock`
- `f_undock()` - removes the parent `Window` to the `Dock` and creates the `Window` in a standalone frame.
- `mousePressEvent(event)` - an event to set the start position of the cursor when dragging the `NavBar`.
- `mouseReleaseEvent(event)` - on release, the window should be maximised to fit the monitor it predominantly occupies.
- `mouseMoveEvent(event)` - reposition the window while the user is holding and dragging the cursor.

# Window Subclass Overview

In the below sections are more details about the implementation of each of the three windows in the application.

The bulk of most of these subclasses contain mostly trivial, repetitive defining of attributes for accessing widgets using `self.findChild()` (See example in the `Window` section above for more info).

These should override `attach_data_interface` if a window requires connecting to a `DataInterface` signal.

# Pilot Window

**This window should display:**

- All `VideoStream`s.
- Current `Task` information.
- Temperature and pressure data.
- Critical Alerts
- A 3D model of the ROV
- Timer


**Signal Connections:**

-  `App` `task_checked()` -> `on_task_change()`
- `DataInterface` `video_stream_update(i)` -> `update_video_data(i)`



**Methods:**

- `on_task_change()` - The current and next tasks are retrieved and all associated widgets are updated. Current and next tasks are not necessarily contiguous.
- `attach_data_interface()` - Connects to `DataInterface` signals.
- `update_video_data()` - Called when the `video_stream_update` signal is emmitted. Displays the new frame on the UI for the *i*th camera. 

# Copilot Window

**This window should display:**

- Sensor data from the ROV via the `DataInterface`
- ROV settings
- **Stdout** from the ROV and UI
- Actions
- Alerts
- Main `VideoStream`
- Task Checklist
- Timer

**Signal Connections:**

- `DataInterface` `rov_data_update` -> `update_rov_data`
- `DataInterface` `float_data_update` -> `update_float_data`
- `DataInterface` `video_stream_update` -> `update_video`
- `DataInterface` `stdout_update` -> `update_stdout`

**Methods:**

- `secs_to_minsec(secs)` - Formats an integer **secs** into a string of form **"mm:ss"**
- `start_timer()` - Starts a `QTimer` object if one has not already been started.
- `stop_timer()` - Stops the `QTimer`. The *stop* widget will become *reset*. If this function is called when the timer is already stopped, it will reset the timer and set all `Task`s to incomplete.
- `timer_timeout()` - Called every second. Updates the timer widgets through `update_time`.
- `update_time()` - Updates the progress bar and remaining text label.
- `build_task_widgets()` - Used in `__init__` to add all `Task` widgets to the `TaskList` container. The `TaskList` is also resized to fit the number of task widgets added. A scrollbar will appear if these overflow.
- `reinitalise_cameras()` - Called when the associated `Action` button is pressed. Each `VideoStream` is re-initialised with `start_init_camera_feed()`
- `check_camera_initialisation_complete()` - Connected to `App`'s `camera_initialisation_complete` signal which is emitted from a `VideoStream` when it successfully initialises. This checks if all `VideoStreams` are finishing trying to initialise so the `Action` button can be unchecked.
- `set_sonar_value(widget, value, value_max` - Set sonar widgets's text to "<vale> cm". If the value exceeds *value_max* then "<value_max> cm" is displayed instead.
- `update_stdout()` - Consumes the `lines_to_add` attribute of `DataInterface` and appends it to the stdout UI widget.
- `update_rov_data()` - If the ROV is connected, it will display the latest values stored in `DataInterface`. Otherwise, all ROV attributes will display "ROV Disconnected".
- `update_float_data()` - If the Float is connected, it will display the latest values stored in `DataInterface`. Otherwise, all Float attributes will display "Float Disconnected."
- `update_video()` - Called when the `video_stream_update` signal is emmitted. Displays the new frame on the UI for the main camera. Any other camera event is ignored.

### ActionThread

This class inherits from Thread.

Actions are functions that the user can perform in the UI when a `QRadioButton` is pressed.
These may take some time to complete and so they run **asynchronously** to the main thead to prevent freezing.

A new action can assigned using the `ActionThread` class.

E.g.
![](README-IMAGES/actionthread.png)

`ActionThread` takes two required arguments and one optional argument:

- action - The `QRadioButton` to bind to.
- target - The main function which should run when the `action` is clicked.
- retain_state(optional. defaults to **False**) - If set to **True**, the action is togglable. 

