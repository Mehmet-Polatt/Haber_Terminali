# 🌐 Haber Terminali | Entelektüel Bilgi & Arşiv Ajanı

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React Native](https://img.shields.io/badge/React_Native-Expo-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://expo.dev)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-1.5_Flash-8E44AD?style=for-the-badge&logo=google-gemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com)

---

## 🎯 Proje Vizyonu

**Haber Terminali**, günlük haber akışındaki clickbait (tık tuzağı), partizan gürültü ve holiganizmi filtreleyerek; olayların arkasındaki **rasyonel argümanları**, **taktiksel/stratejik gerçekleri** ve **2005 sonrası tarihsel bağlamı** sunan kişisel bir yapay zeka asistanıdır.

Medya organlarındaki sansasyonel üsluptan arındırılmış, entelektüel derinliğe sahip ve tarafsız bir analiz deneyimi sağlamayı amaçlar.

---

## 🏗️ Mimari Yaklaşım: İsteğe Bağlı Analiz (On-Demand Analysis)

Haber Terminali, yapay zeka kotasını verimli kullanmak ve sistem performansını optimize etmek için **"İsteğe Bağlı Analiz (On-Demand Analysis)"** mimarisini benimser.

```mermaid
flowchart TD
    A[Haber Kaynakları & Scrapers] -->|Ham Başlık & Özet| B[(MySQL Veritabanı)]
    B -->|Veri Listeleme| C[Mobil Uygulama / React Native UI]
    C -->|Kullanıcı "✨ Yapay Zeka ile Analiz Et" Butonuna Basar| D[Asenkron Gemini API Çağrısı]
    D -->|gemini-1.5-flash Analizi| E[Derinlemesine Rasyonel Analiz & Kart Oluşturma]
    E -->|Veritabanı Güncelleme & Ön Yüz UI| C
```

### 💡 Çalışma Prensibi:
1. **Veri Toplama (Scraping):** Arka planda çalışan scraping servisleri (Playwright, HTTPX), haber kaynaklarından yalnızca **ham başlık** ve **özetleri** toplayarak veritabanına kaydeder.
2. **Rota / Kota Koruması:** Google Gemini API kotalarını harcamamak ve maliyet/hız optimizasyonu sağlamak adına otomatik toplu analiz yapılmaz.
3. **Asenkron Analiz:** Yapay zeka analizi, yalnızca kullanıcı mobil uygulamada ilgili haberin **"✨ Yapay Zeka ile Analiz Et"** butonuna dokunduğunda tetiklenir ve asenkron olarak işlenip arayüze sunulur.

---

## 💻 Kullanılan Teknolojiler (Tech Stack)

### 🔹 Backend
- **Dil & Framework:** Python 3.11+, FastAPI
- **ORM & Veritabanı:** SQLAlchemy (Async ORM), MySQL (`aiomysql` sürücüsü)
- **Web Scraping:** Playwright (TBMM vb. dinamik içerikler için), HTTPX, BeautifulSoup4
- **Servis Yönetimi:** Uvicorn, Asyncio

### 📱 Frontend (Mobil Uygulama)
- **Framework & Araçlar:** React Native, Expo (SDK 51+)
- **HTTP İstemcisi:** Axios
- **UI & Tasarım:** Custom Sleek Dark Mode, Responsive Layouts

### 🧠 Yapay Zeka (AI Engine)
- **Model:** Google Gemini API (`gemini-1.5-flash`)
- **SDK:** `google-genai` / `google-generativeai`
- **Özellikler:** Structured JSON Output, Prompt Engineering, Fallback Mechanisms

---

## 📰 Kategoriler ve Veri Kaynakları

Haber Terminali, farklı alanlardaki güvenilir veri kaynaklarını düzenli olarak tarar:

| Kategori | Kaynaklar | Scraping Yöntemi |
|---|---|---|
| **💻 Teknoloji** | Webrazzi, Anadolu Ajansı (Bilim & Teknoloji), DonanımHaber | HTTPX + RSS + HTML Parsing |
| **🏛️ Siyaset** | BBC Türkçe, T24, Sabah, Sözcü, Gazete Oksijen | Asenkron HTML Scrapers |
| **📜 TBMM (Özel Sekme)** | TBMM Yasama Haberleri | Playwright (Headless Browser ile dinamik DOM çekimi) |
| **⚽ Futbol** | GZT Spor, Sporx, DHA, Transfer Radar, NTV Spor, Futboo, Fanatik | HTTPX + Custom Selectors |

---

## ✨ Öne Çıkan Özellikler

- **⚖️ Kutupsuz ve Rasyonel Argüman Çıkarımı:** Olayları ideolojik veya duygusal dil yerine mantık ve veriye dayalı rasyonel argümanlarla özetler.
- **📜 2005 Sonrası Sınırlandırılmış Tarihsel Arka Plan:** Haberle ilgili tarihsel bağlamı 2005 yılı ve sonrası gelişmelerle sınırlayarak güncel ve alakalı tutar.
- **📚 Kavramsal Sözlük (Core Concept & Definition):** Haberde geçen karmaşık terminoloji veya kilit kavramları tespit edip açık metin tanımlarını sunar.
- **💬 Gemini ile Derinleş:** Kullanıcının seçtiği haber için özel ve detaylı bir derinleşme prompt'u oluşturur, otomatik olarak panoya kopyalar ve tek tıkla doğrudan **Gemini** mobil uygulamasına/web arayüzüne yönlendirir.
- **🛡️ Hata Yönetimi & Dayanıklılık:** 
  - **60 Saniyelik AI Timeout** süresi ile takılan istekler sonlandırılır.
  - **Rate-limit koruması** ve otomatik retry mekanizmaları ile kesintisiz deneyim sağlanır.

---

## 🚀 Kurulum ve Geliştirici Ortamı

Projeyi yerel geliştirme ortamınızda çalıştırmak için aşağıdaki adımları izleyebilirsiniz.

### 📋 Ön Gereksinimler
- **Python 3.11+**
- **Node.js (v18+)** ve **npm / yarn**
- **MySQL Server** (veya uyumlu bir MariaDB örneği)
- **Google Gemini API Key**

---

### 1️⃣ Veritabanı ve `.env` Yapılandırması

Projenin kök dizininde bir `.env` dosyası oluşturun ve aşağıdaki değişkenleri tanımlayın:

```env
DATABASE_URL=mysql+aiomysql://kullanici_adi:sifre@localhost:3306/haber_terminali
GEMINI_API_KEY=your_gemini_api_key_here
```

---

### 2️⃣ Backend Kurulumu ve Başlatılması

```bash
# Kök dizinde sanal ortam oluşturun ve aktif edin
python -m venv .venv
source .venv/bin/activate  # Windows için: .venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Playwright tarayıcılarını kurun (TBMM scraper için gerekli)
playwright install chromium

# Veritabanı tablolarını başlatın
python init_db.py

# FastAPI sunucusunu başlatın
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **API Dokümantasyonu:** Sunucu çalıştıktan sonra Swagger UI arayüzüne [http://localhost:8000/docs](http://localhost:8000/docs) adresinden ulaşabilirsiniz.

---

### 3️⃣ Mobil Uygulamayı (Frontend) Çalıştırma

```bash
# Mobil uygulama dizinine geçin
cd mobil

# Bağımlılıkları yükleyin
npm install

# Expo geliştirme sunucusunu başlatın
npx expo start
```

*QR kodu okutarak **Expo Go** uygulamasında veya bir simülatör (iOS Simulator / Android Emulator) üzerinde test edebilirsiniz.*

---

## 📜 Lisans

Bu proje kişisel araştırma ve entelektüel haber takibi amacıyla geliştirilmiştir. Tüm hakları saklıdır.
