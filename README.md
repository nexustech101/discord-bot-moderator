# Discord Bot Moderator

A modular, production-ready **Discord moderation and survey bot** designed to help community owners automate chat management, gather feedback, and analyze engagement. Built using Python and the Discord API, it supports role management, surveys, moderation, analytics, and optional external integrations.

---

## 🚀 Features

### 🧩 Core Modules

#### **1. User & Role Management**

* Automatically assigns roles (e.g., `New Member`, `Verified`, `VIP`).
* Supports role-based permissions and channel access.
* Optional verification system (captcha, email, or web login).

#### **2. Chat Moderation**

* Detects and deletes spam, profanity, or banned keywords.
* Issues warnings or temporary mutes for offenders.
* Logs deleted messages, warnings, and moderation events.
* Supports command-based channel locking/unlocking.

#### **3. Survey & Feedback System**

* Create surveys or polls directly from Discord commands.
* Supports multiple question types (MCQ, scales, short answers).
* Stores results in a local database (SQLite by default).
* Exports survey results to CSV/JSON.
* Optionally syncs data to Google Sheets, Notion, or Airtable.

#### **4. Analytics & Insights**

* Tracks engagement metrics (messages per day, top users, etc.).
* Generates basic charts and summaries of survey responses.
* Can send automated weekly or monthly reports to admin channels.

#### **5. Admin Tools & Dashboard**

* Role-based admin commands (e.g., `!createsurvey`, `!announce`, `!viewlogs`).
* Modular command toggling (enable/disable moderation, surveys, etc.).
* Optional Flask/FastAPI dashboard for configuration and analytics.

#### **6. Security & Reliability**

* Secrets managed through `.env` file.
* Graceful error handling and logging with timestamps.
* Rate-limit and exception recovery.
* Optional user whitelisting for sensitive commands.

---

## 🏗️ Project Structure

```
/discord-bot-moderator
│
├── bot.py                  # Main entry point
├── config.py               # Environment variable and config loader
├── requirements.txt        # Dependencies
├── README.md               # Project documentation
│
├── cogs/                   # Modular bot components
│   ├── moderation.py       # Handles message filtering and moderation
│   ├── surveys.py          # Manages survey creation and responses
│   ├── analytics.py        # Logs and engagement insights
│   └── integrations.py     # External API integrations
│
├── utils/                  # Utility helpers
│   ├── logger.py           # Logging utilities
│   ├── db_manager.py       # Database abstraction layer
│   └── helpers.py          # Miscellaneous helper functions
│
└── data/
    ├── surveys.db          # SQLite database (default)
    └── logs/               # Log storage
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/nexustech101/discord-bot-moderator.git
cd discord-bot-moderator
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
DISCORD_TOKEN=your_discord_bot_token_here
PREFIX=!
DATABASE_URL=sqlite:///data/surveys.db
ADMIN_ROLE=Admin
```

### 5. Run the Bot

```bash
python bot.py
```

Once running, invite your bot to a Discord server and test commands such as `!help`, `!createsurvey`, or `!announce`.

---

## 🧪 Testing Your Bot

1. **Create a Test Server** in Discord.
2. **Invite the bot** using the OAuth URL generated from your Developer Portal.
3. **Test commands**:

   * `!createsurvey` → Start a new survey.
   * `!announce` → Send an announcement.
   * `!warn @user` → Test moderation.
   * `!stats` → View engagement metrics.
4. **Review logs** inside `data/logs/` to ensure events are recorded correctly.

---

## 🧰 Tech Stack

* **Language:** Python 3.10+
* **Discord Library:** `discord.py` (v2.3+)
* **Database:** SQLite (default) or PostgreSQL (optional)
* **Web Framework (optional):** Flask or FastAPI
* **Environment Management:** python-dotenv
* **Logging:** built-in `logging` + rotating file handler

---

## 🔒 Security Notes

* Never hardcode your Discord token.
* Restrict admin commands to specific roles.
* Store sensitive configs in `.env` and exclude it from version control.
* Use a separate test server before deploying to production.

---

## 🧱 Future Roadmap

* [ ] Add web-based admin dashboard (Flask/FastAPI).
* [ ] Implement advanced analytics visualization.
* [ ] Add integration for Google Sheets or Notion.
* [ ] Add persistent settings per Discord server.
* [ ] Dockerize deployment for scalable hosting.

---

## 🧑‍💻 Contributing

Contributions are welcome! Fork the repo, create a feature branch, and submit a pull request.

```bash
git checkout -b feature/your-feature-name
git commit -m "Add your feature description"
git push origin feature/your-feature-name
```

---

## 🪪 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 💬 Support

For issues, feature requests, or collaboration inquiries:

* Open a GitHub issue
* Or contact **NexusTech101** directly via GitHub

---

> **Note:** This bot is in active development. Expect rapid iteration and improvements.
