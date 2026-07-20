#Pythonは基本的に；不要(改行で終了)
#importは最初に書く
import vlc
import time
import keyboard
import json

#プレイヤー作成
player = vlc.MediaPlayer("music/ムーンライトSad倍速.mp3")
#sasasa
#再生
player.play()

bpm = 71
beat_time = 60000 / bpm

last_beat = -1

#記録した時間を格納する配列
notes = []

key_position = {
    "1":0,
    "2":1,
    "3":2,
    "4":3,
    "5":4,
    "6":5,
    "7":6,
    "8":7
}
#表示場所記憶用変数
position = 0
#Pythonはインデントで1ブロックになる
#無限ループ
def add_note(time,position):
    note = {
        "time":time,
        "position":position
    }
    notes.append(note)
    print("記録：", note)
    #文字列で受け取るから整数型じゃ動かない
    #while keyboard.is_pressed(position):
    #time.sleep(0.01)

#同じ列だと範囲外になる
while True:
    #現在の時刻を取得
    current_time = player.get_time()
    current_time_auto = round(current_time / beat_time)
    current_time_munual = current_time / beat_time


    if current_time_auto != last_beat and current_time_auto % 2 == 0:
        print("現在拍：", current_time_auto)
        #add_note((current_time_auto * beat_time), 0)

    # 表示した拍を記憶
    last_beat = current_time_auto
    #items : 辞書のアイテムをセット(行単位)で取り出す
    #キーが押されているか順番に確認し押されていたら記録する
    for key, position in key_position.items():
        if keyboard.is_pressed(key):
            add_note((current_time_munual * beat_time), position)
            

        while keyboard.is_pressed(key):
            time.sleep(0.01)

    #キーボードのEnterが押されたら
    
    if keyboard.is_pressed("q"):
        break
    
    #"Enter"か"q"が押された時だけ記録する
    #Enterかqが押されるまで止まってしまう(ループが回らない)
    #command = input("Enterで記録、qで終了：")

    #指定した秒数待つ(MediaPlayer側とのずれによって完璧な値にはならない)
    time.sleep(0.01)

#キーボードからの入力を待つ
#入力されるまでここで止まる、入力されたら進む
#input("Enterキーで終了")

#記録した時間を表示
print(notes)

#open : ファイル名,モード(w = 書き込み), コーディング形式 
#with open ~ ファイルを開いて,処理が終わり次第自動で閉じる
with open("notes.json", "w", encoding="utf-8") as f:
    json.dump(notes, f, indent=4)

print("終了")

#停止
player.stop()