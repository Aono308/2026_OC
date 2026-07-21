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
BGM_PATH = "bgm1.mp3"
SHEET_PATH = "notes.json"

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

    # STEP 1: HandLandmarker の初期化
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # STEP 2: カメラの初期化（フルHD要求）
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"カメラ解像度: {actual_w} x {actual_h}")
    # Tkinterウィンドウのセットアップ
    root = tk.Tk()
    root.title('Hand Landmarker - FHD Rhythm Game')
    
    label = tk.Label(root)
    label.pack()

    running = [True]

    def on_closing():
        running[0] = False
    root.protocol("WM_DELETE_WINDOW", on_closing)

    def on_key(event):
        if event.char == 'q':
            running[0] = False
    root.bind('<Key>', on_key)

    print("\n 終了するには、ウィンドウ上で 'q' キーを押すか、ウィンドウを閉じてください。")

    game_started = False
    num_lanes = 8
    scroll_time = 2000
    note_radius = 20  # フルHDに合わせて少し大きめに調整

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

        # 画面中央および要素の座標定義
        center_x, center_y = w // 2, h // 2
        start_x, start_y = center_x, center_y + 100
        start_radius = 40

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
            annotated_image, "Touch to Start", (center_x - 180, center_y - 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3, cv2.LINE_AA
        )
        cv2.circle(annotated_image, (start_x, start_y), start_radius, (255, 255, 255), -1)
        cv2.circle(annotated_image, (start_x, start_y), start_radius + 8, (0, 255, 255), 3)
        
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
    if os.path.exists(BGM_PATH) and running[0]:
        pygame.mixer.music.load(BGM_PATH)
        pygame.mixer.music.play()

        while cap.isOpened() and running[0]:
            success, frame = cap.read()
            if not success:
                print("カメラからの映像取得に失敗しました。")
                break

            frame = np.ascontiguousarray(cv2.flip(frame, 1))
            h, w, _ = frame.shape
            
            center_x, center_y = w // 2, h // 2
            judge_radius = int(h * 0.35)  # 判定ライン半径（画面高さの38%）

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
            cv2.circle(annotated_image, (center_x, center_y), judge_radius, (255, 255, 0), 4)

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
                                cv2.putText(
                                    annotated_image, "HIT!", (note_x - 30, note_y - 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3
                                )

                    cv2.circle(annotated_image, (note_x, note_y), note_radius, (255, 0, 0), -1)
                    cv2.circle(annotated_image, (note_x, note_y), note_radius, (255, 255, 255), 2)

            pil_image = Image.fromarray(annotated_image)
            imgtk = ImageTk.PhotoImage(image=pil_image)

            label.config(image=imgtk)
            label.image = imgtk

            root.update_idletasks()
            root.update()

    cap.release()
    root.destroy()
    print("プログラムを終了しました。")

if __name__ == "__main__":
    main()