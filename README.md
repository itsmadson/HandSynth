# MadHand
MadHand is an innovative MIDI controller that uses computer vision to translate hand movements into musical notes. By leveraging webcam input and hand tracking technology, it allows users to create music through intuitive gestures.
MadHand uses MediaPipe for hand tracking and converts the position of your hand into MIDI notes. The vertical position of your index finger determines the note, while the thumb controls velocity. Making a fist holds the current note.


## Installation

### Download
Download the latest release for your operating system from our [Releases page](https://github.com/itsmadson/madhand/releases).

### MIDI Controller Setup
1. Install [**loopMIDI**](https://www.tobias-erichsen.de/software/loopmidi.html) and create a virtual MIDI port.
2. In the MadHand application, select the created virtual MIDI port.
3. Use a synthesizer like **Vital** to generate sounds based on the MIDI signals from MadHand.
4. Launch the application
2. Select your MIDI output (virtual MIDI port) device and webcam
3. Adjust settings as desired
4. Click "RUN" to start
5. Use your hand to control MIDI output
6. Click "STOP" when finished
   
![image](https://github.com/user-attachments/assets/de9b9717-0c53-4424-b1b1-bc4a8ce3098e)

## Features
- Real-time hand tracking to MIDI conversion
- Adjustable note range and smoothing
- Multi-channel MIDI output
- Graphical user interface for easy configuration
- Command-line script version for advanced users

## Dependencies
The following dependencies are required for the script-only version:
- OpenCV
- MediaPipe
- Mido
- NumPy
- PyQt5


### Script-Only Version
If you prefer to run the script version or want to set up a development environment:

1. Ensure you have Python 3.7 or later installed.
2. Install the required dependencies:
3. Clone the repository:
    ```sh
    git clone https://github.com/itsmadson/MadHand.git
    cd MadHand
    ```
4. Install the required dependencies:
    ```sh
    pip install opencv-python mediapipe mido numpy pyqt5
    ```
5. Run the script:
    ```sh
    python madhand.py
    ```

## Acknowledgments

- [MediaPipe](https://mediapipe.dev/) for hand tracking technology
- [Mido](https://mido.readthedocs.io/) for MIDI functionality
- [OpenCV](https://opencv.org/) for video processing
- [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) for virtual MIDI port creation
- [Vital](https://vital.audio/) for sound synthesis



