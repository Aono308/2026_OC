import os
import urllib.request
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles

# ==========================================================
# 1. 必要なファイル（モデルとテスト画像）を自動ダウンロードするための設定
# ==========================================================
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
MODEL_PATH = "pose_landmarker.task"
IMAGE_URL = "https://cdn.pixabay.com/photo/2019/03/12/20/39/girl-4051811_960_720.jpg"
IMAGE_PATH = "image.jpg"

def download_file(url, filepath):
    """ファイルが存在しない場合のみ自動でダウンロードするヘルパー関数"""
    if not os.path.exists(filepath):
        print(f"'{filepath}' が見つかりません。{url} からダウンロード中...")
        urllib.request.urlretrieve(url, filepath)
        print("ダウンロードが完了しました。")

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
# 3. メインの処理プロセス
# ==========================================================
def main():
    # 必要なファイルをダウンロード
    download_file(MODEL_URL, MODEL_PATH)
    download_file(IMAGE_URL, IMAGE_PATH)

    # STEP 2: PoseLandmarker のオブジェクトを作成
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        output_segmentation_masks=True  # 背景切り抜き用マスクも出力する
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    # STEP 3: 入力画像を読み込み (MediaPipe独自のImageクラスを使用)
    image = mp.Image.create_from_file(IMAGE_PATH)

    # STEP 4: 姿勢のランドマークを検出
    print("推論を実行中...")
    detection_result = detector.detect(image)

    # STEP 5: 結果の可視化と処理
    # ① 骨格ランドマークを描画した画像の生成
    annotated_image = draw_landmarks_on_image(image.numpy_view(), detection_result)
    
    # MediaPipeはRGBを基準にしているため、OpenCV（BGR）で表示できるように変換
    display_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)

    # ② セグメンテーション（切り抜き）マスクが有効な場合、その可視化処理
    if detection_result.segmentation_masks:
        segmentation_mask = detection_result.segmentation_masks[0].numpy_view()
        segmentation_mask = np.squeeze(segmentation_mask)

        # マスクデータを 3チャンネルの 8bit画像（0〜255）に変換して可視化
        visualized_mask = (segmentation_mask * 255).astype(np.uint8)
        visualized_mask = np.stack([visualized_mask] * 3, axis=-1)
        
        # マスク画像をウィンドウ表示
        cv2.imshow('Segmentation Mask', visualized_mask)

    # ランドマークを描画した画像をウィンドウ表示
    cv2.imshow('Pose Landmarker Result', display_image)
    
    print("\n画像を別ウィンドウで表示しました。")
    print("画像のウィンドウをアクティブにした状態で、何かキーを押すとプログラムを終了します。")
    
    # キー入力を待機し、ウィンドウを閉じる
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
