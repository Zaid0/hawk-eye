import requests
import cv2
import numpy as np

url = "http://192.168.1.147/capture"

while True:
    img_resp = requests.get(url)
    img_arr = np.frombuffer(img_resp.content, np.uint8)
    frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

    cv2.imshow("Snapshot", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
