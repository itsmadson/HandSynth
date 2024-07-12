import cv2
import mediapipe as mp
import mido
import time
import numpy as np
import collections

# Adjustable parameters
DEBUG = True
NOTE_CHANGE_THRESHOLD = 6  # Increase this value to reduce sensitivity
SMOOTHING_WINDOW_SIZE = 8 # Adjust this to change smoothing amount
MIN_NOTE = 21  # A0 (lowest note on a standard piano)
MAX_NOTE = 108  # C8 (highest note on a standard piano)

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}")

# Initialize MIDI output
try:
    available_ports = mido.get_output_names()
    debug_print(f"Available MIDI ports: {available_ports}")
    
    if not available_ports:
        print("No MIDI ports available. Please ensure your MIDI device is connected and try again.")
        exit()

    print("Available MIDI ports:")
    for i, port in enumerate(available_ports):
        print(f"{i}: {port}")
    
    port_num = int(input("Enter the number of the MIDI port you want to use: "))
    midi_port = mido.open_output(available_ports[port_num])
    print(f"Connected to MIDI port: {available_ports[port_num]}")
except Exception as e:
    print(f"Error initializing MIDI: {e}")
    exit()

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Initialize webcam
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Set higher frame rate if supported
cap.set(cv2.CAP_PROP_FPS, 60)

# Initialize history for smoothing
note_history = collections.deque(maxlen=SMOOTHING_WINDOW_SIZE)
velocity_history = collections.deque(maxlen=SMOOTHING_WINDOW_SIZE)

def hand_to_midi(hand_landmarks):
    global note_history, velocity_history
    
    # Use the y-coordinate of the index finger tip for note
    # Map the full height of the camera to the full MIDI note range
    raw_note = int(np.interp(hand_landmarks.landmark[8].y, [0, 1], [MAX_NOTE, MIN_NOTE]))
    
    # Use the y-coordinate of the thumb tip for velocity
    raw_velocity = int(np.interp(hand_landmarks.landmark[4].y, [0, 1], [127, 30]))
    
    # Add to history
    note_history.append(raw_note)
    velocity_history.append(raw_velocity)
    
    # Calculate smoothed values
    note = int(sum(note_history) / len(note_history))
    velocity = int(sum(velocity_history) / len(velocity_history))
    
    return note, velocity

def is_fist(hand_landmarks):
    # Check if the fingertips are below the middle phalanges
    return all(hand_landmarks.landmark[tip].y > hand_landmarks.landmark[mid].y 
               for tip, mid in [(8,6), (12,10), (16,14), (20,18)])

last_note = None
last_time = time.time()
hold_note = False

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            debug_print("Ignoring empty camera frame.")
            continue

        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        results = hands.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        debug_print(f"Hand detected: {results.multi_hand_landmarks is not None}")

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                fist = is_fist(hand_landmarks)
                if fist:
                    hold_note = True
                    debug_print("Fist detected, holding note")
                else:
                    hold_note = False
                    debug_print("Hand open, ready to change note")

                note, velocity = hand_to_midi(hand_landmarks)
                debug_print(f"Smoothed note: {note}, velocity: {velocity}")

                if not hold_note and (last_note is None or abs(note - last_note) >= NOTE_CHANGE_THRESHOLD):
                    if last_note is not None:
                        for channel in range(16):
                            midi_port.send(mido.Message('note_off', note=last_note, channel=channel))
                            debug_print(f"Sent Note Off: {last_note} on channel {channel}")
                    for channel in range(16):
                        midi_port.send(mido.Message('note_on', note=note, velocity=velocity, channel=channel))
                        debug_print(f"Sent Note On: {note}, Velocity: {velocity} on channel {channel}")
                    last_note = note
                    last_time = time.time()

        elif last_note is not None and time.time() - last_time > 0.1:
            for channel in range(16):
                midi_port.send(mido.Message('note_off', note=last_note, channel=channel))
                debug_print(f"Sent Note Off (no hand): {last_note} on channel {channel}")
            last_note = None

        cv2.imshow('Hand Controlled Synthesizer', image)
        if cv2.waitKey(5) & 0xFF == 27:  
            break

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    cap.release()
    cv2.destroyAllWindows()
    midi_port.close()
    print("Program ended.")