import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles
import tkinter as tk           # 追加
from PIL import Image, ImageTk # ImageTkを追加
import math
import random
import pygame
import json

# ==========================================================
# 1. 設定（すでにローカルにあるモデルのパスを指定）
# ==========================================================
MODEL_PATH = "pose_landmarker.task"
BGM_PATH = "bgm1.mp3"
SHEET_PATH = "sheet.json"

# ファイルが存在するか念のためチェック（エラー防止）
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"'{MODEL_PATH}' が見つかりません。このスクリプトと同じフォルダにファイルを置くか、"
        "MODEL_PATH の絶対パスを書き換えてください。"
    )

# ==========================================================
# 2. ランドマーク描画用のヘルパー関数
# ==========================================================
def draw_landmarks_on_image(rgb_image, detection_result):
    pose_landmarks_list = detection_result.pose_landmarks
    annotated_image = np.copy(rgb_image)

    pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
    pose_connection_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)

    for pose_landmarks in pose_landmarks_list:
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=pose_landmarks,
            connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=pose_landmark_style,
            connection_drawing_spec=pose_connection_style
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
            "time" : item["time"], #叩くべき目標時間
            "position" : item["position"], #ノーツの位置（0~7）
            "active" : True #ノーツの状態
        })
    pygame.mixer.init()

    if os.path.exists(BGM_PATH):
        pygame.mixer.music.load(BGM_PATH)
        pygame.mixer.music.play(-1) #-1：無限ループ


    # STEP 1: ローカルのモデルから PoseLandmarker を初期化
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=False  # ゲーム用に処理を軽くするため一旦False
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    # STEP 2: カメラの初期化
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    #ノーツの設定
    notes = []
    for _ in range(10): #ループ変数指定なしでループ
        notes.append({
            "x": random.randint(80, 560),
            "y": random.randint(80, 400),
            "active": True
        })
    note_radius = 10 #ノーツの半径（ピクセル）
    # note_active = [True] #ノーツが存在するかどうか
    # note_x = 320 #ノーツのx座標
    # note_y = 240 #ノーツのy座標

    # --- [追加] Tkinterウィンドウのセットアップ ---
    root = tk.Tk()
    root.title('Pose Landmarker - PIL/Tkinter Display')
    
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

    print("\n============================================")
    print("カメラを起動しました（PIL＆Tkinter版）。")
    print("終了するには、ウィンドウ上で 'q' キーを押すか、ウィンドウを閉じてください。")
    print("============================================\n")

    while cap.isOpened() and running[0]:
        success, frame = cap.read()
        if not success:
            print("カメラからの映像取得に失敗しました。")
            break

        # 鏡のように表示するために左右反転（メモリの連続性を確保）
        frame = np.ascontiguousarray(cv2.flip(frame, 1))
        # OpenCV(BGR)からRGBへ変換
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # NumPy配列からMediaPipeのImageオブジェクトを作成
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        # 姿勢推定の実行
        detection_result = detector.detect(mp_image)

        if detection_result.pose_landmarks:
            # 1人目の手の座標を取り出す
            right_hand = detection_result.pose_landmarks[0][19] #右手の平
            left_hand = detection_result.pose_landmarks[0][20] #左手の平

            rx, ry = int(right_hand.x * 640), int(right_hand.y * 480) #右手のx座標,y座標
            lx, ly = int(left_hand.x * 640), int(left_hand.y * 480)
           
            for i, note in enumerate(notes):
                if note["active"]:
                    distance_r = math.sqrt((rx - note["x"]) ** 2 + (ry - note["y"]) ** 2) #右手との距離
                    distance_l = math.sqrt((lx - note["x"]) ** 2 + (ly - note["y"]) ** 2) #左手との距離
                    
                    if distance_l < note_radius or distance_r < note_radius:
                        note["active"] = False

        # 結果を画像に描画
        annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)
        for note in notes:
            if note["active"]:
                cv2.circle(annotated_image, (note["x"], note["y"]), note_radius, (255, 0, 0), -1)#-1:塗りつぶし
                cv2.circle(annotated_image, (note["x"], note["y"]), note_radius, (255, 255, 255), 3)
        # --- [変更点] PILとTkinterによる画面更新 ---
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

if __name__ == "__main__":
    main()