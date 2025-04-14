# Guide for setting up ROV Interface

`rov_interface.py` is the main file that lets the ROV communicate with the UI. 
Please read the following to ensure necessary dependencies are installed and that the ROV and UI can communicate correctly.

## Dependencies

The following files/directories from this git repo need to be installed on the **ROV** for the `rov_interface` to work:

- `source/datainterface/rov_interface.py`
- `source/datainterface/sock_stream_recv.py`
- `source/datainterface/sock_stream_send.py`
- `source/datainterface/video_stream.py` (Will most likely be deprecated in future)
- `source/data_classes`

Additionally, please install the ROV-specific requirements by running `pip install -r rov_requirments.txt`

## Configuring networking (Work in Progress)

Connect your computer, the system that will run the UI, to a router.

Connect the ROV (Raspberry Pi) to the same router.

On the system that will run the UI, run `ipconfig` to find the **IPv4 Address** of your computer on the router's network.
In `source/datainterface/rov_interface.py` on the Raspberry Pi, navigate to the bottom of the file. Set the following parameters of ROVInterface:

- **local_test** = False (This sets up the ROV to listen to incoming connections from other devices)
- **ui_ip** = <The IPv4 Address obtained from running `ipconfig` on your system>

The bottom of this file should then look something like this:

![Example of correctly configured ROVInterface](/../../README-IMAGES/ROVInterfaceexample.png)

Next, run `ifconfig` on the Raspberry Pi to find it's **IPv4 Address** on the router's network.

On your computer, navigate to main.py and set **ROV_IP** to this IPv4 Address. Also set **RUN_LOCALLY** to *False*.

### Additional Notes

_It is recommended to set the IPs of your computer and the ROV to static on this router's network._

_Disable firewall protections that may block communication between the two devices._ (This could be expanded to be more specific).

## You should now be all set up to begin interacting with the ROV through the UI!
