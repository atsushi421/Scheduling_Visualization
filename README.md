# Scheduling_Visualization

## Overview
スケジューリング結果の可視化ツールです。以下に出力例を示します。

<img src="https://user-images.githubusercontent.com/55824710/187318197-64a59624-1ea5-449b-96b7-2696d722597d.svg" width="50%"><img src="https://user-images.githubusercontent.com/55824710/187318194-322aedb0-82fb-478d-8d0d-d0f64612547b.svg" width="50%">

## Setup Flow
```
git clone https://github.com/atsushi421/PaperErrorChecker.git
cd Scheduling_Visualization
./setup.bash
```

## Usage
使い方は以下の通り。スケジューリング結果は HTML ファイルとして出力される。

```
usage: gannt_chart.py [-h] -s SRC_FILE_PATH [-d DEST_DIR] -y Y_AXIS [-hdm] [-l]

optional arguments:
  -h, --help            show this help message and exit
  -s SRC_FILE_PATH, --src_file_path SRC_FILE_PATH
                        The path to source json file
  -d DEST_DIR, --dest_dir DEST_DIR
                        The path to dest result file
  -y Y_AXIS, --y_axis Y_AXIS
                        y_axis. ["core", "task"]
  -hdm, --highlight_deadline_miss
                        Highlight tasks in which deadline misses occurred
  -l, --draw_legend     Draw a legend for each task
```

### Input JSON format
```
{
    "makespan": [int],
    "taskSet": [
        {
            "coreID": [int],
            "taskID": [int],
            "jobID": [int],
            "releaseTime": [int],  // optional
            "deadline": [int],  // optional
            "startTime": [int],
            "finishTime": [int],
            "preemption": [bool],  // optional
            "deadlineMiss": [bool]  // optional
        },
    ...
    ]
}
```
- `// optional` と書かれている項目は記述されていなくても OK
- "releaseTime", "deadline", "preemption" は、`--y_axis task` とした場合に、各ジョブに対して描画される
- `"deadlineMiss": True` とした場合、`--highlight_deadline_miss` オプションを使用すると、そのジョブが赤色に描画される
- マルチレートDAGスケジューリングを前提としているため、jobID の入力が必須になっている。シングルレートDAGのスケジューリング結果を可視化したい場合は、jobID に適当な数字を入れてください（例えば 0）
