# Imports

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import math
from enum import IntEnum
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from google.protobuf.json_format import MessageToDict
import screen_brightness_control as sbcontrol

pyautogui.FAILSAFE = False
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Gesture Encodings 
class Gest(IntEnum):
    # Binary Encoded
    """
    Enum for mapping all hand gesture to binary number.
    """

    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16    
    PALM = 31
    
    # Extra Mappings
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36
    INDEX_FINGER_EXTENDED = 6 
    DOUBLE_CLICK = 7

# Multi-handedness Labels
class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

# Convert Mediapipe Landmarks to recognizable Gestures
class HandRecog:
    """
    Convert Mediapipe Landmarks to recognizable Gestures.
    """
    
    def __init__(self, hand_label):
        """
        Constructs all the necessary attributes for the HandRecog object.

        Parameters
        ----------
            finger : int
                Represent gesture corresponding to Enum 'Gest',
                stores computed gesture for current frame.
            ori_gesture : int
                Represent gesture corresponding to Enum 'Gest',
                stores gesture being used.
            prev_gesture : int
                Represent gesture corresponding to Enum 'Gest',
                stores gesture computed for previous frame.
            frame_count : int
                total no. of frames since 'ori_gesture' is updated.
            hand_result : Object
                Landmarks obtained from mediapipe.
            hand_label : int
                Represents multi-handedness corresponding to Enum 'HLabel'.
        """

        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label
        self.pinky_shown = False
        self.prev_pinky_state = False
        self.n_key_pressed = False
    
    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        """
        returns signed euclidean distance between 'point'.

        Parameters
        ----------
        point : list contaning two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        # Determine the sign based on the y-coordinate of the landmark points
        # Calculate the Euclidean distance between the landmark points
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist*sign
    
    def get_dist(self, point):
        """
        returns euclidean distance between 'point'.

        Parameters
        ----------
        point : list contaning two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        # Extract the coordinates of the landmark points
        # Calculate the squared Euclidean distance
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        # Calculate the euclidean distance
        dist = math.sqrt(dist)
        return dist
    
    def get_dz(self,point):
        """
        returns absolute difference on z-axis between 'point'.

        Parameters
        ----------
        point : list contaning two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)
    
    # Function to find Gesture Encoding using current finger_state.
    # Finger_state: 1 if finger is open, else 0
    def set_finger_state(self):
        """
        set 'finger' by computing ratio of distance between finger tip 
        , middle knuckle, base knuckle.

        Returns
        -------
        None
        """
        if self.hand_result == None:
            return

        points = [[8,5,0],[12,9,0],[16,13,0],[20,17,0]]
        self.finger = 0
        self.finger = self.finger | 0 #thumb
        for idx,point in enumerate(points):
            
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])
            
            try:
                ratio = round(dist/dist2,1)
            except:
                ratio = round(dist/0.01,1)

            self.finger = self.finger << 1
            if ratio > 0.5 :
                self.finger = self.finger | 1
    

    # Handling Fluctations due to noise
    def get_gesture(self):
        """
        returns int representing gesture corresponding to Enum 'Gest'.
        sets 'frame_count', 'ori_gesture', 'prev_gesture', 
        handles fluctations due to noise.
        
        Returns
        -------
        int
        """
        if self.hand_result == None:
            return Gest.PALM

        current_gesture = Gest.PALM
        if self.finger in [Gest.LAST3,Gest.LAST4] and self.get_dist([8,4]) < 0.05:
            if self.hand_label == HLabel.MINOR :
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        # if self.finger == 8:
        #     current_gesture = Gest.INDEX_FINGER_EXTENDED       
        # if self.hand_result is not None:
        #     if self.get_dist([4, 12]) < 1:  # Adjust threshold as needed
        #         # Perform double-click action
        #         # pyautogui.doubleClick()
        #         current_gesture = Gest.DOUBLE_CLICK  
        # if self.hand_result is not None:
        #     if self.get_dz([4,12]) < 0.5:
        #         current_gesture = Gest.DOUBLE_CLICK                                                        

        elif Gest.FIRST2 == self.finger:                        
            point = [[8,12],[5,9]]                                                                      
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1/dist2
            if ratio > 1:#1.7
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8,12]) < 2:
                    current_gesture =  Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture =  Gest.MID
        
        elif self.finger == 1:
            current_pinky_state = True
            current_gesture = Gest.INDEX_FINGER_EXTENDED
                
            
        else:
            current_gesture =  self.finger
        
        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0
        self.prev_gesture = current_gesture

        if self.frame_count > 4 :
            self.ori_gesture = current_gesture
        return self.ori_gesture

# Executes commands according to detected gestures
class Controller:
    """
    Executes commands according to detected gestures.

    Attributes
    ----------
    tx_old : int
        previous mouse location x coordinate
    ty_old : int
        previous mouse location y coordinate
    flag : bool
        true if V gesture is detected
    grabflag : bool
        true if FIST gesture is detected
    pinchmajorflag : bool
        true if PINCH gesture is detected through MAJOR hand,
        on x-axis 'Controller.changesystembrightness', 
        on y-axis 'Controller.changesystemvolume'.
    pinchminorflag : bool
        true if PINCH gesture is detected through MINOR hand,
        on x-axis 'Controller.scrollHorizontal', 
        on y-axis 'Controller.scrollVertical'.
    pinchstartxcoord : int
        x coordinate of hand landmark when pinch gesture is started.
    pinchstartycoord : int
        y coordinate of hand landmark when pinch gesture is started.
    pinchdirectionflag : bool
        true if pinch gesture movment is along x-axis,
        otherwise false
    prevpinchlv : int
        stores quantized magnitued of prev pinch gesture displacment, from 
        starting position
    pinchlv : int
        stores quantized magnitued of pinch gesture displacment, from 
        starting position
    framecount : int
        stores no. of frames since 'pinchlv' is updated.
    prev_hand : tuple
        stores (x, y) coordinates of hand in previous frame.
    pinch_threshold : float
        step size for quantization of 'pinchlv'.
    """

    tx_old = 0
    ty_old = 0
    trial = True
    flag = False
    grabflag = False
    pinchmajorflag = False
    pinchminorflag = False
    pinchstartxcoord = None
    pinchstartycoord = None
    pinchdirectionflag = None
    prevpinchlv = 0
    pinchlv = 0
    framecount = 0
    prev_hand = None
    pinch_threshold = 0.3
    
    def getpinchylv(hand_result):
        """returns distance beween starting pinch y coord and current hand position y coord."""
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y)*10,1)
        return dist

    def getpinchxlv(hand_result):
        """returns distance beween starting pinch x coord and current hand position x coord."""
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord)*10,1)
        return dist
    
    def changesystembrightness():
        """sets system brightness based on 'Controller.pinchlv'."""
        currentBrightnessLv = sbcontrol.get_brightness(display=0)[0]/100.0
        currentBrightnessLv += Controller.pinchlv/20.0
        if currentBrightnessLv > 1.0:
            currentBrightnessLv = 1.0
        elif currentBrightnessLv < 0.0:
            currentBrightnessLv = 0.0       
        sbcontrol.fade_brightness(int(100*currentBrightnessLv) , start = sbcontrol.get_brightness(display=0)[0])
    
    def changesystemvolume():
        """sets system volume based on 'Controller.pinchlv'."""
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()
        currentVolumeLv += Controller.pinchlv/20.0
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)
    
    def scrollVertical():
        """scrolls on screen vertically."""
        pyautogui.scroll(200 if Controller.pinchlv>0.0 else -200)
        
    
    def scrollHorizontal():
        """scrolls on screen horizontally."""
        pyautogui.keyDown('shift')
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(-120 if Controller.pinchlv>0.0 else 120)
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('shift')

    # Locate Hand to get Cursor Position
    # Stabilize cursor by Dampening
    def get_position(hand_result):
        """
        returns coordinates of current hand position.

        Locates hand to get cursor position also stabilize cursor by 
        dampening jerky motion of hand.

        Returns
        -------
        tuple(float, float)
        """
        point = 9
        position = [hand_result.landmark[point].x ,hand_result.landmark[point].y]
        sx,sy = pyautogui.size()
        x_old,y_old = pyautogui.position()
        x = int(position[0]*sx)
        y = int(position[1]*sy)
        if Controller.prev_hand is None:
            Controller.prev_hand = x,y
        delta_x = x - Controller.prev_hand[0]
        delta_y = y - Controller.prev_hand[1]

        distsq = delta_x**2 + delta_y**2
        ratio = 1
        Controller.prev_hand = [x,y]

        if distsq <= 25:
            ratio = 0
        elif distsq <= 900:
            ratio = 0.07 * (distsq ** (1/2))
        else:
            ratio = 2.1
        x , y = x_old + delta_x*ratio , y_old + delta_y*ratio
        return (x,y)

    def pinch_control_init(hand_result):
        """Initializes attributes for pinch gesture."""
        Controller.pinchstartxcoord = hand_result.landmark[8].x
        Controller.pinchstartycoord = hand_result.landmark[8].y
        Controller.pinchlv = 0
        Controller.prevpinchlv = 0
        Controller.framecount = 0

    # Hold final position for 5 frames to change status
    def pinch_control(hand_result, controlHorizontal, controlVertical):
        """
        calls 'controlHorizontal' or 'controlVertical' based on pinch flags, 
        'framecount' and sets 'pinchlv'.

        Parameters
        ----------
        hand_result : Object
            Landmarks obtained from mediapipe.
        controlHorizontal : callback function assosiated with horizontal
            pinch gesture.
        controlVertical : callback function assosiated with vertical
            pinch gesture. 
        
        Returns
        -------
        None
        """
        if Controller.framecount == 5:
            Controller.framecount = 0
            Controller.pinchlv = Controller.prevpinchlv

            if Controller.pinchdirectionflag == True:
                controlHorizontal() #x

            elif Controller.pinchdirectionflag == False:
                controlVertical() #y

        lvx =  Controller.getpinchxlv(hand_result)
        lvy =  Controller.getpinchylv(hand_result)
            
        if abs(lvy) > abs(lvx) and abs(lvy) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = False
            if abs(Controller.prevpinchlv - lvy) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvy
                Controller.framecount = 0

        elif abs(lvx) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = True
            if abs(Controller.prevpinchlv - lvx) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvx
                Controller.framecount = 0

    def handle_controls(gesture, hand_result):  
        prev_pinky_state = False
        current_pinky_state = False
        prev_pinky_state = False
        n_key_pressed =False
        """Impliments all gesture functionality."""      
        x,y = None,None
        if gesture != Gest.PALM :
            x,y = Controller.get_position(hand_result)
            
        # flag reset
        if gesture != Gest.FIST and Controller.grabflag:
            Controller.grabflag = False
            pyautogui.mouseUp(button = "left")

        if gesture != Gest.PINCH_MAJOR and Controller.pinchmajorflag:
            Controller.pinchmajorflag = False

        if gesture != Gest.PINCH_MINOR and Controller.pinchminorflag:
            Controller.pinchminorflag = False

        # implementation
        if gesture == Gest.V_GEST:                                                            
            Controller.flag = True
            pyautogui.moveTo(x, y, duration = 0.09)
            
            # pyautogui.press('space')

        elif gesture == Gest.INDEX_FINGER_EXTENDED and not prev_pinky_state:            
        # Trigger space button press
            if not n_key_pressed:
                pyautogui.press('n')
                n_key_pressed = True
            if not current_pinky_state and prev_pinky_state:
            # Reset the click state when the pinky finger is hidden 
                n_key_pressed = False

        elif gesture == Gest.FIST:
            if not Controller.grabflag : 
                Controller.grabflag = True
                pyautogui.mouseDown(button = "left")
            pyautogui.moveTo(x, y, duration = 0.1)

        elif gesture == Gest.MID and Controller.flag:
            pyautogui.click()
            # pyautogui.sleep(0.5)
            Controller.flag = False

        elif gesture == Gest.INDEX and Controller.flag:
            pyautogui.click(button='right')
            Controller.flag = False
 
        elif gesture == Gest.TWO_FINGER_CLOSED and Controller.flag:
            pyautogui.doubleClick()
            Controller.flag = False

        elif gesture == Gest.PINCH_MINOR:
            if Controller.pinchminorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchminorflag = True
            Controller.pinch_control(hand_result,Controller.scrollHorizontal, Controller.scrollVertical)
        
        elif gesture == Gest.PINCH_MAJOR:
            if Controller.pinchmajorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchmajorflag = True
            Controller.pinch_control(hand_result,Controller.changesystembrightness, Controller.changesystemvolume)
        
'''
----------------------------------------  Main Class  ----------------------------------------
    Entry point of Gesture Controller
'''


class GestureController:
    """
    Handles camera, obtain landmarks from mediapipe, entry point
    for whole program.

    Attributes
    ----------
    gc_mode : int
        indicates weather gesture controller is running or not,
        1 if running, otherwise 0.
    cap : Object
        object obtained from cv2, for capturing video frame.
    CAM_HEIGHT : int
        highet in pixels of obtained frame from camera.
    CAM_WIDTH : int
        width in pixels of obtained frame from camera.
    hr_major : Object of 'HandRecog'
        object representing major hand.
    hr_minor : Object of 'HandRecog'
        object representing minor hand.
    dom_hand : bool
        True if right hand is domaniant hand, otherwise False.
        default True.
    """
    gc_mode = 0
    cap = None
    CAM_HEIGHT = None
    CAM_WIDTH = None
    hr_major = None # Right Hand by default
    hr_minor = None # Left hand by default
    dom_hand = True

    def __init__(self):
        """Initilaizes attributes."""
        GestureController.gc_mode = 1
        GestureController.cap = cv2.VideoCapture(0)
        GestureController.CAM_HEIGHT = GestureController.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        GestureController.CAM_WIDTH = GestureController.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    
    def classify_hands(results):
        """
        sets 'hr_major', 'hr_minor' based on classification(left, right) of 
        hand obtained from mediapipe, uses 'dom_hand' to decide major and
        minor hand.
        """
        left , right = None,None
        try:
            handedness_dict = MessageToDict(results.multi_handedness[0])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]
            else :
                left = results.multi_hand_landmarks[0]
        except:
            pass

        try:
            handedness_dict = MessageToDict(results.multi_handedness[1])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]
            else :
                left = results.multi_hand_landmarks[1]
        except:
            pass
        
        if GestureController.dom_hand == True:
            GestureController.hr_major = right
            GestureController.hr_minor = left
        else :
            GestureController.hr_major = left
            GestureController.hr_minor = right

    def start(self):
        """
        Entry point of whole programm, caputres video frame and passes, obtains
        landmark from mediapipe and passes it to 'handmajor' and 'handminor' for
        controlling.
        """
        
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)

        with mp_hands.Hands(max_num_hands = 1,min_detection_confidence=0.3, min_tracking_confidence=0.3) as hands:
            while GestureController.cap.isOpened() and GestureController.gc_mode:
                success, image = GestureController.cap.read()
                image_height,image_width,_ = image.shape

                if not success:
                    print("Ignoring empty camera frame.")
                    continue
                
                image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = hands.process(image)
                
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                if results.multi_hand_landmarks:                   
                    GestureController.classify_hands(results)
                    handmajor.update_hand_result(GestureController.hr_major)
                    handminor.update_hand_result(GestureController.hr_minor)

                    handmajor.set_finger_state()
                    handminor.set_finger_state()
                    gest_name = handminor.get_gesture()
                    color = (255, 0, 0)

                    def get_bounding_box(hand_landmarks):
                        """Calculate the bounding box coordinates of the hand."""
                        x_values = [landmark.x for landmark in hand_landmarks.landmark]
                        y_values = [landmark.y for landmark in hand_landmarks.landmark]
                        x_min = int(min(x_values) * image_width)
                        x_max = int(max(x_values) * image_width)
                        y_min = int(min(y_values) * image_height)
                        y_max = int(max(y_values) * image_height)
                        return x_min, y_min, x_max, y_max

                    if gest_name == Gest.PINCH_MINOR:
                        Controller.handle_controls(gest_name, handminor.hand_result)
                    else:
                        gest_name = handmajor.get_gesture()
                        Controller.handle_controls(gest_name, handmajor.hand_result)
                    
                    for hand_landmarks in results.multi_hand_landmarks:
                        # mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                        
                        # Get the landmark coordinates you want to draw a circle around
                        # For example, if you want to draw a circle around the tip of the index finger (landmark point 8):
                         # Extract the bounding box coordinates of the hand
                        x_min, y_min, x_max, y_max = get_bounding_box(hand_landmarks)

                        # Draw a rectangle around the hand
                        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 8)  # Adjust color and thickness as needed
                        index_finger_tip = hand_landmarks.landmark[8]
                        thumb_finger_tip = hand_landmarks.landmark[4]
                        middle_finger_tip = hand_landmarks.landmark[12]
                        ring_finger_tip = hand_landmarks.landmark[16]
                        pinky_finger_tip = hand_landmarks.landmark[20]
                        
                        # Convert landmark coordinates to pixel values
                        image_height, image_width, _ = image.shape
                        ax, ay = int(index_finger_tip.x * image_width), int(index_finger_tip.y * image_height)
                        bx, by = int(thumb_finger_tip.x * image_width), int(thumb_finger_tip.y * image_height)
                        cx, cy = int(middle_finger_tip.x * image_width), int(middle_finger_tip.y * image_height)
                        dx, dy = int(ring_finger_tip.x * image_width), int(ring_finger_tip.y * image_height)
                        ex, ey = int(pinky_finger_tip.x * image_width), int(pinky_finger_tip.y * image_height)
                        
                        # Draw a circle around the landmark point
                        cv2.circle(image, (ax, ay), radius=10, color=(0, 255, 0), thickness=2)
                        cv2.circle(image, (bx, by), radius=10, color=(0, 255, 0), thickness=2)
                        cv2.circle(image, (cx, cy), radius=10, color=(0, 255, 0), thickness=2)
                        cv2.circle(image, (dx, dy), radius=10, color=(0, 255, 0), thickness=2)
                        cv2.circle(image, (ex, ey), radius=10, color=(0, 255, 0), thickness=2)

                else:
                    Controller.prev_hand = None
                cv2.namedWindow('Gesture Controller', cv2.WINDOW_NORMAL)  # Create a resizable window
                cv2.setWindowProperty('Gesture Controller', cv2.WND_PROP_TOPMOST, 1)
                cv2.resizeWindow('Gesture Controller', 500, 500)
                cv2.imshow('Gesture Controller', image)           
                if cv2.waitKey(5) & 0xFF == 13:
                    break
        GestureController.cap.release()
       
        cv2.destroyAllWindows()

# uncomment to run directlyṇ
gc1 = GestureController()
gc1.start()      