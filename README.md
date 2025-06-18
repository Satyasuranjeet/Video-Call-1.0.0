# VideoCall Model

A modern, full-stack video calling application featuring a FastAPI WebSocket signaling server and a beautiful React + Vite + Tailwind CSS frontend. Easily host secure, real-time video calls with screen sharing, chat, and more.

---

## Features

- **Real-time video calls** with multiple participants (WebRTC)
- **Screen sharing** and media controls (mute/unmute, camera on/off)
- **Text chat** during calls
- **Room-based architecture** (create or join rooms)
- **Responsive, modern UI** (React, Tailwind CSS)
- **FastAPI WebSocket signaling server**
- **Easy local development** (Vite, hot reload)
- **Deployable to Vercel or any cloud**

---

## Project Structure

```
VideoCall-Model/
├── server/         # FastAPI WebSocket signaling server (Python)
│   ├── app.py
│   ├── requirements.txt
│   └── vercel.json
└── video-call/     # React + Vite frontend (JavaScript)
    ├── src/
    ├── public/
    ├── package.json
    ├── vite.config.js
    └── README.md
```

---

## Getting Started

### 1. Backend: FastAPI Signaling Server

#### Install dependencies
```bash
cd server
python -m venv temp
source temp/Scripts/activate  # On Windows: temp\Scripts\activate
pip install -r requirements.txt
```

#### Run the server
```bash
python app.py
```
- The server runs at `http://localhost:8000`
- WebSocket endpoint: `ws://localhost:8000/ws/{room_id}?name={user_name}`

### 2. Frontend: React + Vite App

#### Install dependencies
```bash
cd video-call
npm install
```

#### Start the development server
```bash
npm run dev
```
- The app runs at `http://localhost:3000`

---

## Usage

1. Open the frontend in your browser: [http://localhost:3000](http://localhost:3000)
2. Enter your name and create a new room, or join an existing room with its ID.
3. Share the room ID with others to join the same call.
4. Use the controls to mute/unmute, toggle video, share your screen, or leave the call.

---

## API Endpoints (Server)

- `GET /` — Server status
- `GET /health` — Health check
- `GET /rooms` — List active rooms
- `GET /rooms/{room_id}` — Room info
- `WS /ws/{room_id}?name=...` — WebSocket signaling for video calls

---

## Deployment

- The backend can be deployed to Vercel (see `server/vercel.json`) or any cloud provider.
- The frontend can be built with `npm run build` and deployed to Vercel, Netlify, or any static host.

---

## Tech Stack

- **Frontend:** React, Vite, Tailwind CSS
- **Backend:** FastAPI, WebSockets, Uvicorn
- **Signaling:** WebSocket (custom protocol)
- **Peer-to-peer:** WebRTC

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
