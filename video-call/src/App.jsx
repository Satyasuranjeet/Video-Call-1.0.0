"use client"

import { useState } from "react"
import HomePage from "./components/HomePage"
import VideoRoom from "./components/VideoRoom"
import "./App.css"

function App() {
  const [currentView, setCurrentView] = useState("home")
  const [roomData, setRoomData] = useState(null)

  const joinRoom = (roomId, userName) => {
    setRoomData({ roomId, userName })
    setCurrentView("room")
  }

  const leaveRoom = () => {
    setCurrentView("home")
    setRoomData(null)
  }

  return (
    <div className="App">
      {currentView === "home" && <HomePage onJoinRoom={joinRoom} />}
      {currentView === "room" && roomData && (
        <VideoRoom roomId={roomData.roomId} userName={roomData.userName} onLeaveRoom={leaveRoom} />
      )}
    </div>
  )
}

export default App
