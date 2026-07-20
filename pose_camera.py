import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import tkinter as tk
from PIL import Image, ImageTk
import math
import random
import pygame
import json

# ==========================================================
# 1. 設定（すでにローカルにあるモデルのパスを指定）
# ==========================================================
MODEL_PATH = "hand_landmarker.task"
BGM_PATH = "bgm1.mp3"
SHEET_PATH = "notes.json"

# ファイルが存在するか念のためチェック（エラー防止）
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"'{MODEL_PATH}' が見つかりません。このスクリプトと同じフォルダにファイルを置くか、"
        "MODEL_PATH の絶対パスを書き換えてください。"
    )

# ==========================================================
# 2. ランドマーク描画用のヘルパー関数
# ==========================================================
HAND_CONNECTIONS = [ #どの座標を線で結ぶか
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]

def draw_landmarks_on_image(rgb_image, detection_result):
    annotated_image = np.copy(rgb_image)#画像のコピー作成

    for hand_landmarks in detection_result.hand_landmarks:

        points = [] #各関節の座標を保存

        for landmark in hand_landmarks:
            x = int(landmark.x * annotated_image.shape[1]) #mediapipeから届く座標 * 画像の幅でピクセル座標を計算
            y = int(landmark.y * annotated_image.shape[0])

            points.append((x, y))

            cv2.circle(#円を描画する関数
                annotated_image, #入力画像
                (x, y), #中心位置
                4, #半径
                (0, 255, 0), #色
                -1 #線の種類
            )

        for start_idx, end_idx in HAND_CONNECTIONS:
            cv2.line(#線を描画する関数
                annotated_image,
                points[start_idx],#始点
                points[end_idx],#終点
                (255, 0, 0),
                2
            )

    return annotated_image

# ==========================================================
# 3. メイン処理
# ==========================================================
def main():
    with open(SHEET_PATH, "r", encoding="utf-8") as f: #jsonファイルから譜面を読み込み
        sheet_data = json.load(f)

    notes = []
    for item in sheet_data:
        notes.append({
            "time" : item["time"], #叩くべき目標時間
            "position" : item["position"], #ノーツの位置（0~7）
            "active" : True #ノーツの状態
        })
    pygame.mixer.init()

    


    # STEP 1: ローカルのモデルから PoseLandmarker を初期化
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2 #認識可能な手の数
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # STEP 2: カメラの初期化
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    #ノーツの設定
    num_lanes = 8
    center_x, center_y = 320, 240 #画面の中心座標
    judge_radius = 240 #中心から判定ラインまでの距離
    scroll_time = 1000 #2000ms
    note_radius = 20

    # --- [追加] Tkinterウィンドウのセットアップ ---
    root = tk.Tk()
    root.title('Hand Landmarker - PIL/Tkinter Display')
    
    # 映像描画用ラベル
    label = tk.Label(root)
    label.pack()

    # 制御用フラグ（スコープ対応のためリストにしています）
    running = [True]

    # ウィンドウの「×」ボタンが押されたとき
    def on_closing():
        running[0] = False
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # ウィンドウをアクティブにした状態で「q」キーが押されたとき
    def on_key(event):
        if event.char == 'q':
            running[0] = False
    root.bind('<Key>', on_key)

    print("\n 終了するには、ウィンドウ上で 'q' キーを押すか、ウィンドウを閉じてください。")

    game_started = False

    start_x, start_y = 320, 280
    start_radius = 20 

    while cap.isOpened() and running[0]:
        success, frame = cap.read()
        if not success:
            print("カメラからの映像取得に失敗しました。")
            break

        # 鏡のように表示するために左右反転（メモリの連続性を確保）
        frame = np.ascontiguousarray(cv2.flip(frame, 1))#水平方向反転
        current_time = pygame.mixer.music.get_pos() #現在の再生時間
        # OpenCV(BGR)からRGBへ変換
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # NumPy配列からMediaPipeのImageオブジェクトを作成
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        #手の骨格推定の実行
        detection_result = detector.detect(mp_image)
        active_pointer_positions = []
        # 結果を画像に描画
        annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)

        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                judge_point = hand_landmarks[9]
                fx = int(judge_point.x * 640)
                fy = int(judge_point.y * 480)
                active_pointer_positions.append((fx, fy))

                cv2.circle(annotated_image, (fx, fy), 10, (0, 255, 255), -1)

        #スタート画面
        cv2.putText(annotated_image, "ここに触れたら始まります", (130, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3, cv2.LINE_AA)
        cv2.circle(annotated_image, (start_x, start_y), start_radius, (255, 255, 255), -1)
        cv2.circle(annotated_image, (start_x, start_y), start_radius + 5, (255, 255, 255), -1)
        
        for fx, fy in active_pointer_positions:
            distance = math.sqrt((fx - start_x) ** 2 + (fy - start_y) ** 2)
            if distance < (start_radius + 30):
                game_started = True
                break

        if game_started:
            break

        pil_image = Image.fromarray(annotated_image)
        # 2. ImageTk 形式へ変換
        imgtk = ImageTk.PhotoImage(image=pil_image)
        # print(f"現在の座標： {detection_result}")
        # 3. GUIの画像表示をアップデート
        label.config(image=imgtk)
        label.image = imgtk
        # 4. ウィンドウ全体の更新（描画を即時反映）
        root.update_idletasks()
        root.update()
    #BGM再生
    if os.path.exists(BGM_PATH) and running[0]:
        pygame.mixer.music.load(BGM_PATH)
        pygame.mixer.music.play() #-1：無限ループ

        #ゲーム開始
        while cap.isOpened() and running[0]:
            success, frame = cap.read()
            if not success:
                print("カメラからの映像取得に失敗しました。")
                break

            # 鏡のように表示するために左右反転（メモリの連続性を確保）
            frame = np.ascontiguousarray(cv2.flip(frame, 1))#水平方向反転
            current_time = pygame.mixer.music.get_pos() #現在の再生時間
            # OpenCV(BGR)からRGBへ変換
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # NumPy配列からMediaPipeのImageオブジェクトを作成
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            #手の骨格推定の実行
            detection_result = detector.detect(mp_image)
            active_pointer_positions = []
            # 結果を画像に描画
            annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)

            if detection_result.hand_landmarks:
                for hand_landmarks in detection_result.hand_landmarks:
                    judge_point = hand_landmarks[9]
                    fx = int(judge_point.x * 640)
                    fy = int(judge_point.y * 480)
                    active_pointer_positions.append((fx, fy))
                    cv2.circle(annotated_image, (fx, fy), 10, (0, 255, 255), -1)
            
            cv2.circle(annotated_image, (center_x, center_y), judge_radius, (255, 255, 0), 3)#円形の判定ライン

            for i in range(num_lanes):
                angle = i * (2 * math.pi / num_lanes) #360度を8等分
                line_end_x = int(center_x + 300 * math.cos(angle))
                line_end_y = int(center_y + 300 * math.sin(angle))
                cv2.line(annotated_image, (center_x, center_y), (line_end_x, line_end_y),(100,100,100), 1 )


            for note in notes:
                color = (255, 0, 0)
                if not note["active"]:#noteがactiveでない（叩かれていたら）無視
                    continue

                target_time = note["time"]
                position = note["position"]

                if target_time - scroll_time <= current_time <=target_time + 150:
                    ratio = (current_time - (target_time - scroll_time)) / scroll_time
                    angle = position * (2 * math.pi / num_lanes) #positionにより角度を決定
                    current_distance = ratio * judge_radius #現在の時間に応じた中心からの距離
                    note_x = int(center_x + current_distance * math.cos(angle))
                    note_y = int(center_y + current_distance * math.sin(angle))

                    time_diff = abs(current_time - target_time)

                    if time_diff <= 150:
                        for fx, fy in active_pointer_positions:
                            distance = math.sqrt((fx - note_x) ** 2 + (fy - note_y) ** 2)
                            if distance < (note_radius + 35):
                                note["active"] = False
                                cv2.putText(annotated_image, "HIT!", (note_x - 20, judge_radius - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)

                    cv2.circle(annotated_image, (note_x, note_y), note_radius, color, -1)
                    cv2.circle(annotated_image, (note_x, note_y), note_radius, (255, 255, 255), 2)

            # PILとTkinterによる画面更新
            # 1. NumPy（RGB）を PIL Image へ変換
            pil_image = Image.fromarray(annotated_image)

            # 2. ImageTk 形式へ変換
            imgtk = ImageTk.PhotoImage(image=pil_image)

            # print(f"現在の座標： {detection_result}")
            # 3. GUIの画像表示をアップデート
            label.config(image=imgtk)
            label.image = imgtk

            # 4. ウィンドウ全体の更新（描画を即時反映）
            root.update_idletasks()
            root.update()

    # クリーンアップ（cv2.destroyAllWindowsは不要になりました）
    cap.release()
    root.destroy()  # Tkinterのウィンドウを完全に破棄
    print("プログラムを終了しました。")

if __name__ == "__main__":#直接実行されたときのみmain関数を呼び出す
    main()