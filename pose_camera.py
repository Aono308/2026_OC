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
# 1. 設定
# ==========================================================
MODEL_PATH = "hand_landmarker.task"
BGM_PATH = "cutbgm.mp3"
SHEET_PATH = "cut.json"
WIDTH = 1920
HEIGHT = 1080

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"'{MODEL_PATH}' が見つかりません。このスクリプトと同じフォルダにファイルを置くか、"
        "MODEL_PATH の絶対パスを書き換えてください。"
    )

# ==========================================================
# 2. ランドマーク描画用のヘルパー関数
# ==========================================================
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]

def draw_landmarks_on_image(rgb_image, detection_result):
    annotated_image = np.copy(rgb_image)
    h, w, _ = annotated_image.shape

    for hand_landmarks in detection_result.hand_landmarks:
        points = []
        for landmark in hand_landmarks:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            points.append((x, y))

            cv2.circle(annotated_image, (x, y), 6, (0, 255, 0), -1)

        for start_idx, end_idx in HAND_CONNECTIONS:
            cv2.line(
                annotated_image,
                points[start_idx],
                points[end_idx],
                (255, 0, 0),
                3
            )

    return annotated_image

# ==========================================================
# 3. メイン処理
# ==========================================================
def main():
    
        # STEP 1: HandLandmarker の初期化
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2
        )
        detector = vision.HandLandmarker.create_from_options(options)

        # STEP 2: カメラの初期化（フルHD要求）
        # cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap = cv2.VideoCapture(0)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*'MJPG')
        )

        actual_w = int(WIDTH)
        actual_h = int(HEIGHT)

        print(f"カメラ解像度: {actual_w} x {actual_h}")
        # Tkinterウィンドウのセットアップ
        root = tk.Tk()
        root.title('Hand Landmarker - FHD Rhythm Game')
        
        label = tk.Label(root, width=WIDTH, height=HEIGHT)
        label.pack()

        running = [True]

        while True:
            with open(SHEET_PATH, "r", encoding="utf-8") as f:
                    sheet_data = json.load(f)
            notes = []  
            for item in sheet_data:
                notes.append({
                    "time" : item["time"],
                    "position" : item["position"],
                    "active" : True
                })
            pygame.mixer.init()
            

            def on_closing():
                running[0] = False
            root.protocol("WM_DELETE_WINDOW", on_closing)

            def on_key(event):
                if event.char == 'q':
                    # running[0] = False
                    replay_requested = True
                    root.destroy()
            root.bind('<Key>', on_key)
            root.focus_force()

            print("\n 終了するには、ウィンドウ上で 'q' キーを押すか、ウィンドウを閉じてください。")

            game_started = False
            num_lanes = 8
            scroll_time = 2000
            note_radius = 20  # フルHDに合わせて少し大きめに調整
            score = 0

            note_speed_power = 3.0 # 【追加】ノーツの移動カーブ設定
            # ------------------------------------------------------
            # スタート待機ループ
            # ------------------------------------------------------
            while cap.isOpened() and running[0]:
                success, frame = cap.read()
                if not success:
                    print("カメラからの映像取得に失敗しました。")
                    break

                frame = np.ascontiguousarray(cv2.flip(frame, 1))
                h, w, _ = frame.shape  # 実際の解像度を取得（例: 1920x1080）
                judge_radius = int(h * 0.28)  # 判定ライン半径（画面高さのn%）

                # 画面中央および要素の座標定義
                center_x, center_y = w // 2, h // 2
                start_x, start_y = center_x, center_y - 150
                start_radius = 10

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = detector.detect(mp_image)
                
                active_pointer_positions = []
                annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)


                if detection_result.hand_landmarks:
                    for hand_landmarks in detection_result.hand_landmarks:
                        judge_point = hand_landmarks[9]
                        fx = int(judge_point.x * w)  # 実際の幅でスケール
                        fy = int(judge_point.y * h)  # 実際の高さでスケール
                        active_pointer_positions.append((fx, fy))

                        cv2.circle(annotated_image, (fx, fy), 15, (0, 255, 255), -1)

                # スタート画面テキストとボタンを描画
                cv2.putText(
                    annotated_image, "Touch to Start", (center_x - 160, center_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3, cv2.LINE_AA
                )

                cv2.putText(
                    annotated_image, "黄色の円全体に触れる位置に立ってください", (center_x - 400, center_y - 350),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3, cv2.LINE_AA
                )
                
                cv2.circle(annotated_image, (start_x, start_y + 30), start_radius, (255, 255, 255), -1)
                cv2.circle(annotated_image, (start_x, start_y + 30), start_radius + 8, (0, 255, 255), 3)
                cv2.circle(annotated_image, (center_x, center_y - 30), judge_radius, (255, 255, 0), 4)
                
                for fx, fy in active_pointer_positions:
                    distance = math.sqrt((fx - start_x) ** 2 + (fy - start_y) ** 2)
                    if distance < (start_radius + 30):
                        game_started = True
                        break

                if game_started:
                    break

                pil_image = Image.fromarray(annotated_image)
                imgtk = ImageTk.PhotoImage(image=pil_image)
                label.config(image=imgtk)
                label.image = imgtk
                root.update_idletasks()
                root.update()

            # ------------------------------------------------------
            # メインゲームループ
            # ------------------------------------------------------
            music_started = False #BGMが再生開始されたかのフラグ
            if os.path.exists(BGM_PATH) and running[0]:
                pygame.mixer.music.load(BGM_PATH)
                pygame.mixer.music.play()

                while cap.isOpened() and running[0]:
                    success, frame = cap.read()
                    if not success:
                        print("カメラからの映像取得に失敗しました。")
                        break

                    if pygame.mixer.music.get_busy():
                        music_started = True
                    elif music_started:
                        print("音楽終了")
                        break
                    
                    frame = np.ascontiguousarray(cv2.flip(frame, 1))
                    h, w, _ = frame.shape
                    
                    center_x, center_y = w // 2, h // 2
                    
                    current_time = pygame.mixer.music.get_pos()
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                    
                    detection_result = detector.detect(mp_image)
                    active_pointer_positions = []
                    annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)

                    if detection_result.hand_landmarks:
                        for hand_landmarks in detection_result.hand_landmarks:
                            judge_point = hand_landmarks[9]
                            fx = int(judge_point.x * w)
                            fy = int(judge_point.y * h)
                            active_pointer_positions.append((fx, fy))
                            cv2.circle(annotated_image, (fx, fy), 15, (0, 255, 255), -1)
                    
                    # 判定ライン（円形）を描画
                    cv2.circle(annotated_image, (center_x, center_y - 30), judge_radius, (255, 255, 0), 4)

                    # レーンの放射状ガイドライン描画
                    for i in range(num_lanes):
                        angle = i * (2 * math.pi / num_lanes)
                        line_end_x = int(center_x + (judge_radius + 50) * math.cos(angle))
                        line_end_y = int(center_y + (judge_radius + 50) * math.sin(angle))
                        cv2.line(annotated_image, (center_x, center_y), (line_end_x, line_end_y), (100, 100, 100), 1)

                    # ノーツ移動とヒット判定
                    for note in notes:
                        if not note["active"]:
                            continue

                        target_time = note["time"]
                        position = note["position"]

                        if target_time - scroll_time <= current_time <= target_time + 500:
                            ratio = (current_time - (target_time - scroll_time)) / scroll_time # t
                            ratio = max(0.0, ratio)

                            eased_ratio = ratio ** note_speed_power
                            current_distance = eased_ratio * judge_radius

                            angle = position * (2 * math.pi / num_lanes)
                            note_x = int(center_x + current_distance * math.cos(angle))
                            note_y = int(center_y + current_distance * math.sin(angle))

                            time_diff = abs(current_time - target_time)

                            if time_diff <= 200:
                                for fx, fy in active_pointer_positions:
                                    distance = math.sqrt((fx - note_x) ** 2 + (fy - note_y) ** 2)
                                    if distance < (note_radius + 40):
                                        note["active"] = False
                                        score += 100
                                        print(f"score: {score}")
                                        cv2.putText(
                                            annotated_image, "HIT!", (note_x - 30, note_y - 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3
                                        )

                            cv2.circle(annotated_image, (note_x, note_y), note_radius, (255, 0, 0), -1)
                            cv2.circle(annotated_image, (note_x, note_y), note_radius, (255, 255, 255), 2)

                    score_x = int(w * 0.02)
                    score_y = int(h * 0.08)

                    cv2.putText(
                        annotated_image,
                        f"Score : {score}",
                        (center_x - 630, center_y - 280),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        2,
                        (50, 100, 200),
                        5
                    )

                    pil_image = Image.fromarray(annotated_image)
                    imgtk = ImageTk.PhotoImage(image=pil_image, size=(WIDTH, HEIGHT))

                    label.config(image=imgtk)
                    label.image = imgtk

                    root.update_idletasks()
                    root.update()


            #リザルト
        # ------------------------------------------------------
            # リザルト画面ループ
            # ------------------------------------------------------
            if running[0]:
                replay_requested = False #リプレイフラグ
                print("リザルト画面を表示します")
                def on_key(event):
                    if event.char == 'q':
                        running[0] = False
                        root.destroy()
                root.bind('<Key>', on_key)


                while cap.isOpened() and running[0]:
                    success, frame = cap.read()
                    if not success:
                        break

                    # カメラ映像の取得・反転
                    frame = np.ascontiguousarray(cv2.flip(frame, 1))
                    h, w, _ = frame.shape
                    center_x, center_y = w // 2, h // 2

                    # ボタンの領域設定（画面中央の下側）
                    retry_x, retry_y = center_x, center_y + 140
                    retry_radius = 50

                    # 手の検出（リザルト画面でもタッチ操作を可能にする）
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                    detection_result = detector.detect(mp_image)
                    annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)

                    active_pointer_positions = []
                    if detection_result.hand_landmarks:
                        for hand_landmarks in detection_result.hand_landmarks:
                            fx = int(hand_landmarks[9].x * w)
                            fy = int(hand_landmarks[9].y * h)
                            active_pointer_positions.append((fx, fy))
                            cv2.circle(annotated_image, (fx, fy), 15, (0, 255, 255), -1)

                    # 1. 背景を少し暗くする（オーバーレイ）
                    overlay = annotated_image.copy()
                    cv2.rectangle(
                        overlay,
                        (center_x - 450, center_y - 250),
                        (center_x + 450, center_y + 280),
                        (20, 20, 20),
                        -1
                    )
                    cv2.addWeighted(overlay, 0.7, annotated_image, 0.3, 0, annotated_image)
                    cv2.rectangle(
                        annotated_image,
                        (center_x - 450, center_y - 250),
                        (center_x + 450, center_y + 280),
                        (0, 255, 255),
                        3
                    )

                    # 2. テキスト描画
                    cv2.putText(
                        annotated_image, "GAME CLEAR", (center_x - 260, center_y - 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 255, 255), 5, cv2.LINE_AA
                    )
                    cv2.putText(
                        annotated_image, f"SCORE: {score}", (center_x - 230, center_y - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA
                    )

                    if score >= 4300:
                        cv2.putText(
                            annotated_image, "RANK: SSS", (center_x - 210, center_y + 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA
                        )
                    elif score >= 3500 and score < 4300 :
                        cv2.putText(
                                        annotated_image, "RANK: S", (center_x - 210, center_y + 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA
                                    )
                    elif score >= 2500 and score < 3500:
                        cv2.putText(
                                        annotated_image, "RANK: A", (center_x - 210, center_y + 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA
                                    )
                    elif score >= 1200 and score < 2500:
                        cv2.putText(
                                        annotated_image, "RANK: B", (center_x - 210, center_y + 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA
                                    ) 
                    else:
                        cv2.putText(
                                        annotated_image, "RANK: C", (center_x - 210, center_y + 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4, cv2.LINE_AA
                                    )

                    # 3. 再戦／終了のアナウンステキスト
                    cv2.putText(
                        annotated_image, "Press 'Q' or Close to Exit", (center_x - 150, center_y + 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 180), 2, cv2.LINE_AA
                    )

                    # REPLAY（タイトルへ戻る）ボタン描画
                    cv2.circle(annotated_image, (retry_x, retry_y), retry_radius, (0, 255, 255), -1)
                    cv2.circle(annotated_image, (retry_x, retry_y), retry_radius + 6, (255, 255, 255), 3)
                    cv2.putText(
                        annotated_image, "REPLAY", (retry_x - 50, retry_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 1, cv2.LINE_AA
                    )

                    # 手をかざしてリプレイ（スタート待機画面に戻る）判定
                    for fx, fy in active_pointer_positions:
                        dist = math.sqrt((fx - retry_x) ** 2 + (fy - retry_y) ** 2)
                        if dist < (retry_radius + 30):
                            replay_requested = True
                            break

                    if replay_requested:
                        print("リプレイ：タイトル画面へ戻ります")
                        break

                    # 4. Tkinter画面へ反映
                    pil_image = Image.fromarray(annotated_image)
                    imgtk = ImageTk.PhotoImage(image=pil_image)
                    label.config(image=imgtk)
                    label.image = imgtk



                    root.update_idletasks()
                    root.update()

if __name__ == "__main__":
    main()