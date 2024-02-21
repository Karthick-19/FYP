import cv2
import time
import mediapipe as mp

# To capture video from our system webcam
cam = cv2.VideoCapture(0)

# from mediapipe model we are accessing hands 
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mpDraw = mp.solutions.drawing_utils

# FPS on screen
ptime = 0
ctime = 0
while True:
    success, img = cam.read()

    # hands uses rgb format 
    imgRGB = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    # detect the hand land marks
    if results.multi_hand_landmarks:
        for handlms in results.multi_hand_landmarks:
            # handlams are points and HAND_CONNECTIONS are connecting lines 
            mpDraw.draw_landmarks(img,handlms,mp_hands.HAND_CONNECTIONS)
    
    ctime = time.time()
    fps = 1/(ctime-ptime)
    ptime = ctime

    cv2.putText(img,str(int(fps)),(10,70),cv2.FONT_HERSHEY_PLAIN,3,(255,0,255),3)

    cv2.imshow("Image",img)
    cv2.waitKey(1)         