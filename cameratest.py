import cv2

# 0 を 1 や 2 に変えたり、cv2.CAP_DSHOW を消したりして試せます
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

if not cap.isOpened():
    print("カメラを起動できませんでした。")
    exit()

print("カメラテスト中... 終了するにはキーボードの 'q' を押してください。")
while True:
    ret, frame = cap.read()
    if not ret:
        print("映像データを受け取れません。")
        break
    
    cv2.imshow("Test Window", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()