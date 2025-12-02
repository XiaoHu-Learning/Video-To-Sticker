# 🎬 影片截取 + AI 智能去背工具 (Video to Sticker)

這是一個基於 Python 與 Gradio 開發的工具，專為 **AI 繪圖創作** 與 **LINE 動態貼圖創作** 打造（做 GIF Sticker 應該也非常合適）。

它可以將影片自動拆解成連續圖片，並透過 Rembg 工具包自動去除背景，同時加上了 **DPI 解析度設定** 與 **LINE 動態貼圖規格縮放**兩項功能，最後將成品打包成 ZIP 下載，以簡化動態貼圖製作的流程！

小胡碎碎念：
我們透過 AI 繪圖與影片生成突破個人技術的限制，快速實現腦中的畫面，但目前的 AI 生成技術難以兼顧作品的個人特色與精緻度，所以小胡我會把 AI 生成的圖片再匯入到繪圖軟體（如 Procreate）手動做細部調整，我想這應該可以說是 Human in the loop 吧。人類文明和技術會持續進步的原因，也是因為想逃出這個迴圈，所以不斷地尋找方法、發明新技術。這套工具可以說是在眾多巨人們提出的方法中，小胡我偶然地發現它並把它實踐出來而已。

## ✨ 這套工具的主要功能

- **📹 影片智慧截取**：支援「每隔 X 秒截圖」或「指定總張數」兩種模式。
- **🤖 AI 自動去背**：整合 `rembg`，提供 7 種 AI 模型（包含動漫專用、真人專用、通用型等）。
- **📏 LINE 貼圖規格優化**：內建一鍵縮放至 `320px × 270px` (保持比例)，符合 LINE 動態貼圖規範。
- **🖨️ DPI 解析度設定**：支援 72 \~ 300 DPI 設定，方便後續匯入繪圖軟體（如 Procreate）進行精修。
- **🔧 進階邊緣修飾**：可微調前景/背景閾值與侵蝕大小 (Erode Size)，解決白邊或去背不乾淨的問題。
- **📦 一鍵打包**：所有處理好的圖片自動打包成 ZIP 檔。

## ⚙️ 系統需求 (System Requirements)

在執行此程式之前，請務必確保您的電腦已安裝以下軟體：

### 1\. Python 3.8+

請確保已安裝 Python 環境。

### 2\. FFmpeg (必須安裝 ⚠️)

本專案使用 OpenCV 讀取影片，**必須** 在系統中安裝 FFmpeg 才能支援多種影片格式解碼。

- **Windows:**
  1.  前往 [FFmpeg 下載頁面](https://ffmpeg.org/download.html) 下載 build 檔案。
  2.  解壓縮後，將 `bin` 資料夾的路徑（例如 `C:\ffmpeg\bin`）加入到系統環境變數 (Path) 中。
  3.  開啟 CMD 輸入 `ffmpeg -version` 確認是否安裝成功。
- **macOS (使用 Homebrew):**
  ```bash
  brew install ffmpeg
  ```
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update && sudo apt install ffmpeg
  ```

## 🚀 快速開始

### 1\. 建立並啟動虛擬環境 (推薦)

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2\. 安裝 Python 套件

請確認目錄下有 `requirements.txt` (若無請參考下方建立)，並執行：

```bash
pip install -r requirements.txt
```

> **核心套件列表：**
>
> - `gradio==4.44.1`
> - `gradio_client==1.3.0`
> - `huggingface-hub==0.36.0`
> - `numpy==2.0.2`
> - `onnxruntime`
> - `opencv-python-headless`
> - `pillow`
> - `pydantic==2.10.6`
> - `pydantic_core==2.27.2`
> - `rembg`

### 3\. 執行程式

```bash
python app.py
```

_(請將 `app.py` 替換為您的主程式檔名)_

程式啟動後，瀏覽器會自動開啟操作介面。

## 🤖 AI 模型介紹

本工具內建多種模型，請依據素材類型選擇：

| 模型名稱            | 適用場景  | 說明                                               |
| :------------------ | :-------- | :------------------------------------------------- |
| **u2net**           | 通用      | 預設模型，最穩定，適合大多數情況。                 |
| **isnet-anime**     | 動漫/卡通 | 製作貼圖首選，對線條與二次元畫風有極佳的去背效果。 |
| **u2net_human_seg** | 真人      | 針對人體輪廓優化，適合人物影片。                   |
| **silueta**         | 快速人像  | 體積小、速度快，適合全身照。                       |
| **u2net_cloth_seg** | 衣物      | 只保留衣服，去除人物身體部分。                     |

## 💡 使用小技巧

- **去除白邊/綠幕殘留**：試著調高「侵蝕大小 (Erode Size)」至 5\~10。
- **頭髮細節不見了**：試著降低「前景閾值」。
- **後續要印刷或精修**：請將 DPI 拉至 **300**。
- **LINE 貼圖製作**：在輸出尺寸選擇「LINE 動態貼圖」，程式會自動幫您將長邊縮放至 320px 或 270px 內。

## ❤️ 支持作者

如果您覺得這個工具對您有幫助，歡迎贊助支持小胡持續創作！
[👉 點此贊助 (Portaly)](https://portaly.cc/xiaohu/support)
