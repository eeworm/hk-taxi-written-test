# Driwe 溫習指南 — 的士及網約車綜合筆試免費溫習平台 🚕

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)

一個免費、無需註冊、可完全離線使用嘅溫習平台，幫你準備香港運輸署 **的士及網約車綜合筆試**（Taxi and Ride-hailing Vehicle Combined Written Test）。

🌐 **線上版**：https://eeworm.github.io/hk-taxi-written-test/

## 功能

- 📚 **19 課完整筆記** — 由考試概覽、牌照制度、收費規則、乘客服務、司機行為規範，到全港地方識別、路線規劃、交通標誌分類
- 📝 **互動模擬試** — 200+ 多項選擇題，智能抽題（未答過／曾答錯優先），即時對答案＋詳盡解釋，答題狀態存喺瀏覽器 localStorage（唔會上傳）
- 🗺️ **官方地方及路線題庫** — 255 個地方＋18 條路線（運輸署試題小冊子出處），附 Google Maps 彈窗直接睇位置
- 🚦 **交通標誌圖鑑** — 警告、禁制、指示、資訊標誌官方圖樣內嵌
- 🔍 **全文搜尋**、🌙 深色模式、📱 手機友善
- 💾 **單一 HTML 檔案** — 整個網站就係一個 `index.html`，內嵌全部圖片，download 落嚟離線都得

## 使用方法

### 線上使用
直接開 [https://eeworm.github.io/hk-taxi-written-test/](https://eeworm.github.io/hk-taxi-written-test/)

### 離線使用
下載 [`index.html`](index.html)，雙擊喺瀏覽器開啟就得 —— 冇網絡都用到，完美適合搭車時溫書。

## 免責聲明 ⚠️

- 本平台為**非官方**溫習工具，與香港特別行政區政府運輸署並無關聯，亦未經運輸署認可
- 內容僅供參考，如有出入，**一切以運輸署官方公布為準**
- 交通標誌圖片版權屬**香港特別行政區政府運輸署**所有
- 部分例題來源（星島日報、香港經濟日報、明報、PickMyQuiz 等）已於內文註明

## 授權條款

| 內容 | 授權 |
|------|------|
| 筆記、題庫、程式碼 | [CC BY-NC-SA 4.0](LICENSE)（註明出處・非商業・相同方式共享） |
| 交通標誌圖片 | 版權屬運輸署所有，**不包括**喺上述授權內 |

## GitHub Pages 部署教學

1. 將本 repo fork 到自己帳號
2. 喺 repo 頁面撳 **Settings** → 左邊 **Pages**
3. 「Source」揀 **Deploy from a branch**
4. Branch 揀 **main**，資料夾揀 **/ (root)**，撳 Save
5. 等 1–2 分鐘，網站就會喺 `https://<你的用戶名>.github.io/hk-taxi-written-test/` 上線

> 💡 每次 push 新 commit 到 main，Pages 會自動重新部署。個網站係純靜態檔案（HTML/CSS/JS 全部內嵌喺 `index.html`），唔需要任何伺服器。

## 開發

### 檔案結構

```
├── index.html            ← 生成出嚟嘅網站（整個站就係呢個檔案）
├── build-html.py         ← 構建腳本（將 .md 筆記編譯成 index.html）
├── notes/                ← 課程筆記（Markdown）
├── exams/                ← 練習題庫（Markdown）
├── curriculum/           ← 建議課程大綱
└── assets/signs/         ← 交通標誌圖片（構建時內嵌）
```

### 重新生成網站

改完任何 `.md` 筆記之後：

```bash
python3 -m pip install markdown   # 只需裝一次
python3 build-html.py
```

## 貢獻 🙌

歡迎任何人開 issue 或 pull request：

- 🐛 捉錯：筆記內容有誤或資料過時
- ➕ 加題：喺 `exams/quiz-bank-mc.md` 加選擇題
- ✨ 改進：功能建議、錯字修正

---

🎉 **祝大家考試成功，一take過！**
