"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import VideoControls from "./VideoControls"
import ParticipantVideo from "./ParticipantVideo"

const VideoRoom = ({ roomId, userName, onLeaveRoom }) => {
  const [isConnected, setIsConnected] = useState(false)
  const [participants, setParticipants] = useState([])
  const [localStream, setLocalStream] = useState(null)
  const [isAudioEnabled, setIsAudioEnabled] = useState(true)
  const [isVideoEnabled, setIsVideoEnabled] = useState(true)
  const [isScreenSharing, setIsScreenSharing] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState("Initializing...")
  const [remoteStreams, setRemoteStreams] = useState(new Map())
  const [error, setError] = useState(null)

  const localVideoRef = useRef(null)
  const wsRef = useRef(null)
  const peerConnectionsRef = useRef(new Map())
  const localStreamRef = useRef(null)
  const screenStreamRef = useRef(null)
  const myUserIdRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  // WebRTC configuration with STUN servers
  const rtcConfiguration = {
    iceServers: [
      { urls: "stun:stun.l.google.com:19302" },
      { urls: "stun:stun1.l.google.com:19302" },
      { urls: "stun:stun2.l.google.com:19302" },
      { urls: "stun:stun3.l.google.com:19302" },
      { urls: "stun:stun4.l.google.com:19302" },
    ],
    iceCandidatePoolSize: 10,
  }

  // Get the correct WebSocket URL for Vercel deployment
  const getWebSocketUrl = () => {
    // Always use the Vercel backend
    const backendUrl = "video-call-1-0-0.vercel.app"
    const protocol = "wss:" // Vercel always uses HTTPS/WSS

    return `${protocol}//${backendUrl}/ws/${roomId}?name=${encodeURIComponent(userName)}`
  }

  // Initialize everything when component mounts
  useEffect(() => {
    console.log("🚀 VideoRoom component mounted")
    initializeApp()

    return () => {
      console.log("🧹 VideoRoom component unmounting")
      cleanup()
    }
  }, [roomId, userName])

  const initializeApp = async () => {
    try {
      setError(null)
      setConnectionStatus("Getting camera access...")

      // First get media access
      const stream = await initializeMedia()
      if (!stream) {
        throw new Error("Failed to get media access")
      }

      // Then connect to signaling server
      setConnectionStatus("Connecting to server...")
      await connectToSignalingServer()
    } catch (error) {
      console.error("❌ Failed to initialize app:", error)
      setError(error.message)
      setConnectionStatus("Failed to initialize")
    }
  }

  const initializeMedia = async () => {
    try {
      console.log("🎥 Requesting camera and microphone access...")

      const constraints = {
        video: {
          width: { ideal: 1280, max: 1920 },
          height: { ideal: 720, max: 1080 },
          frameRate: { ideal: 30 },
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      console.log(
        "✅ Got media stream:",
        stream.getTracks().map((t) => `${t.kind}: ${t.label}`),
      )

      setLocalStream(stream)
      localStreamRef.current = stream

      // Set up local video
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream
        localVideoRef.current.muted = true
        try {
          await localVideoRef.current.play()
          console.log("✅ Local video playing")
        } catch (playError) {
          console.log("⚠️ Local video autoplay prevented:", playError)
        }
      }

      return stream
    } catch (error) {
      console.error("❌ Media access error:", error)

      let errorMessage = "Camera/microphone access denied"
      if (error.name === "NotFoundError") {
        errorMessage = "No camera or microphone found"
      } else if (error.name === "NotAllowedError") {
        errorMessage = "Please allow camera and microphone access"
      } else if (error.name === "NotReadableError") {
        errorMessage = "Camera/microphone is being used by another application"
      }

      setError(errorMessage)
      throw new Error(errorMessage)
    }
  }

  const connectToSignalingServer = async () => {
    return new Promise((resolve, reject) => {
      try {
        const serverUrl = getWebSocketUrl()
        console.log("🔌 Connecting to Vercel backend:", serverUrl)

        const ws = new WebSocket(serverUrl)
        wsRef.current = ws

        // Connection timeout
        const timeout = setTimeout(() => {
          if (ws.readyState !== WebSocket.OPEN) {
            ws.close()
            reject(new Error("Connection timeout - Vercel backend may be sleeping"))
          }
        }, 20000) // Longer timeout for Vercel cold starts

        ws.onopen = () => {
          console.log("✅ Connected to Vercel signaling server")
          clearTimeout(timeout)
          setIsConnected(true)
          setConnectionStatus("Connected to Vercel")
          resolve()
        }

        ws.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data)
            console.log("📨 Received message:", message.type, message)
            await handleSignalingMessage(message)
          } catch (error) {
            console.error("❌ Error handling message:", error)
          }
        }

        ws.onclose = (event) => {
          console.log("❌ WebSocket closed:", event.code, event.reason)
          setIsConnected(false)
          setConnectionStatus("Disconnected from Vercel")

          // Try to reconnect if it wasn't intentional
          if (event.code !== 1000 && !reconnectTimeoutRef.current) {
            console.log("🔄 Attempting to reconnect to Vercel...")
            setConnectionStatus("Reconnecting to Vercel...")
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectTimeoutRef.current = null
              if (wsRef.current?.readyState !== WebSocket.OPEN) {
                connectToSignalingServer().catch((error) => {
                  console.error("❌ Reconnection failed:", error)
                  setError("Connection lost to Vercel backend. Please refresh the page.")
                })
              }
            }, 5000) // Longer delay for Vercel
          }
        }

        ws.onerror = (error) => {
          console.error("❌ WebSocket error:", error)
          clearTimeout(timeout)
          setConnectionStatus("Connection failed")

          let errorMessage = "Failed to connect to Vercel backend"
          if (navigator.onLine === false) {
            errorMessage = "No internet connection. Please check your network."
          } else {
            errorMessage = "Cannot connect to Vercel backend. The server may be starting up (cold start)."
          }

          reject(new Error(errorMessage))
        }
      } catch (error) {
        console.error("❌ Error creating WebSocket:", error)
        reject(error)
      }
    })
  }

  const handleSignalingMessage = useCallback(async (message) => {
    switch (message.type) {
      case "room_joined":
        console.log("🏠 Joined room successfully")
        myUserIdRef.current = message.user_id

        // Add existing participants
        if (message.participants && message.participants.length > 0) {
          console.log("👥 Found existing participants:", message.participants)
          setParticipants(message.participants)

          // Create peer connections for existing participants
          for (const participant of message.participants) {
            console.log("🤝 Creating peer connection for existing participant:", participant.name)
            await createPeerConnection(participant.id, true) // We'll be the caller
          }
        }
        break

      case "user_joined":
        console.log("👤 New user joined:", message.user.name)
        setParticipants((prev) => {
          const exists = prev.find((p) => p.id === message.user.id)
          if (!exists) {
            return [...prev, message.user]
          }
          return prev
        })
        break

      case "offer":
        console.log("📞 Received offer from:", message.sender_name)
        await handleOffer(message)
        break

      case "answer":
        console.log("📞 Received answer from:", message.sender_name)
        await handleAnswer(message)
        break

      case "ice-candidate":
        console.log("🧊 Received ICE candidate from:", message.sender_name)
        await handleIceCandidate(message)
        break

      case "user_left":
        console.log("👋 User left:", message.user.name)
        setParticipants((prev) => prev.filter((p) => p.id !== message.user.id))

        // Clean up peer connection
        const pc = peerConnectionsRef.current.get(message.user.id)
        if (pc) {
          pc.close()
          peerConnectionsRef.current.delete(message.user.id)
        }

        setRemoteStreams((prev) => {
          const newStreams = new Map(prev)
          newStreams.delete(message.user.id)
          return newStreams
        })
        break

      case "media-state":
        console.log("🎛️ Media state update from:", message.user.name)
        setParticipants((prev) =>
          prev.map((p) =>
            p.id === message.user.id
              ? { ...p, audioEnabled: message.audio_enabled, videoEnabled: message.video_enabled }
              : p,
          ),
        )
        break

      default:
        console.log("❓ Unknown message type:", message.type)
    }
  }, [])

  const createPeerConnection = async (userId, isInitiator) => {
    console.log(`🔗 Creating peer connection for user ${userId}, isInitiator: ${isInitiator}`)

    try {
      const pc = new RTCPeerConnection(rtcConfiguration)
      peerConnectionsRef.current.set(userId, pc)

      // Add local stream tracks
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((track) => {
          console.log(`➕ Adding ${track.kind} track to peer connection`)
          pc.addTrack(track, localStreamRef.current)
        })
      }

      // Handle incoming remote stream
      pc.ontrack = (event) => {
        console.log(`🎬 Received remote stream from ${userId}`)
        const [remoteStream] = event.streams
        setRemoteStreams((prev) => new Map(prev.set(userId, remoteStream)))
      }

      // Handle ICE candidates
      pc.onicecandidate = (event) => {
        if (event.candidate && wsRef.current?.readyState === WebSocket.OPEN) {
          console.log(`🧊 Sending ICE candidate to ${userId}`)
          wsRef.current.send(
            JSON.stringify({
              type: "ice-candidate",
              candidate: event.candidate,
              target: userId,
            }),
          )
        }
      }

      // Monitor connection state
      pc.onconnectionstatechange = () => {
        console.log(`🔄 Connection state with ${userId}: ${pc.connectionState}`)
        if (pc.connectionState === "failed") {
          console.log(`❌ Connection failed with ${userId}`)
        }
      }

      pc.oniceconnectionstatechange = () => {
        console.log(`🧊 ICE connection state with ${userId}: ${pc.iceConnectionState}`)
      }

      // If we're the initiator, create and send offer
      if (isInitiator) {
        console.log(`📞 Creating offer for ${userId}`)
        const offer = await pc.createOffer({
          offerToReceiveAudio: true,
          offerToReceiveVideo: true,
        })

        await pc.setLocalDescription(offer)

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          console.log(`📤 Sending offer to ${userId}`)
          wsRef.current.send(
            JSON.stringify({
              type: "offer",
              offer: offer,
              target: userId,
            }),
          )
        }
      }

      return pc
    } catch (error) {
      console.error(`❌ Error creating peer connection for ${userId}:`, error)
      throw error
    }
  }

  const handleOffer = async (message) => {
    console.log(`📞 Handling offer from ${message.sender}`)

    try {
      let pc = peerConnectionsRef.current.get(message.sender)
      if (!pc) {
        pc = await createPeerConnection(message.sender, false)
      }

      await pc.setRemoteDescription(new RTCSessionDescription(message.offer))
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        console.log(`📤 Sending answer to ${message.sender}`)
        wsRef.current.send(
          JSON.stringify({
            type: "answer",
            answer: answer,
            target: message.sender,
          }),
        )
      }
    } catch (error) {
      console.error(`❌ Error handling offer:`, error)
    }
  }

  const handleAnswer = async (message) => {
    console.log(`📞 Handling answer from ${message.sender}`)

    try {
      const pc = peerConnectionsRef.current.get(message.sender)
      if (pc) {
        await pc.setRemoteDescription(new RTCSessionDescription(message.answer))
        console.log(`✅ Set remote description for ${message.sender}`)
      }
    } catch (error) {
      console.error(`❌ Error handling answer:`, error)
    }
  }

  const handleIceCandidate = async (message) => {
    console.log(`🧊 Handling ICE candidate from ${message.sender}`)

    try {
      const pc = peerConnectionsRef.current.get(message.sender)
      if (pc && pc.remoteDescription) {
        await pc.addIceCandidate(new RTCIceCandidate(message.candidate))
        console.log(`✅ Added ICE candidate for ${message.sender}`)
      }
    } catch (error) {
      console.error(`❌ Error handling ICE candidate:`, error)
    }
  }

  const toggleAudio = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0]
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled
        setIsAudioEnabled(audioTrack.enabled)
        console.log(`🎤 Audio ${audioTrack.enabled ? "enabled" : "disabled"}`)

        // Notify other participants
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "media-state",
              audio_enabled: audioTrack.enabled,
              video_enabled: isVideoEnabled,
            }),
          )
        }
      }
    }
  }

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0]
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled
        setIsVideoEnabled(videoTrack.enabled)
        console.log(`📹 Video ${videoTrack.enabled ? "enabled" : "disabled"}`)

        // Notify other participants
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "media-state",
              audio_enabled: isAudioEnabled,
              video_enabled: videoTrack.enabled,
            }),
          )
        }
      }
    }
  }

  const toggleScreenShare = async () => {
    try {
      if (!isScreenSharing) {
        console.log("🖥️ Starting screen share...")

        const screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: { mediaSource: "screen" },
          audio: true,
        })

        screenStreamRef.current = screenStream
        const videoTrack = screenStream.getVideoTracks()[0]

        // Replace video track in all peer connections
        const replacePromises = []
        peerConnectionsRef.current.forEach((pc, userId) => {
          const sender = pc.getSenders().find((s) => s.track && s.track.kind === "video")
          if (sender) {
            replacePromises.push(sender.replaceTrack(videoTrack))
          }
        })

        await Promise.all(replacePromises)

        // Update local video
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = screenStream
        }

        setIsScreenSharing(true)
        console.log("✅ Screen sharing started")

        // Handle screen share end
        videoTrack.onended = () => {
          console.log("🛑 Screen share ended")
          stopScreenShare()
        }
      } else {
        await stopScreenShare()
      }
    } catch (error) {
      console.error("❌ Screen sharing error:", error)
      alert("Screen sharing failed: " + error.message)
    }
  }

  const stopScreenShare = async () => {
    console.log("🛑 Stopping screen share...")

    try {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach((track) => track.stop())
        screenStreamRef.current = null
      }

      // Replace with camera track
      if (localStreamRef.current) {
        const videoTrack = localStreamRef.current.getVideoTracks()[0]

        const replacePromises = []
        peerConnectionsRef.current.forEach((pc, userId) => {
          const sender = pc.getSenders().find((s) => s.track && s.track.kind === "video")
          if (sender && videoTrack) {
            replacePromises.push(sender.replaceTrack(videoTrack))
          }
        })

        await Promise.all(replacePromises)

        // Update local video
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = localStreamRef.current
        }
      }

      setIsScreenSharing(false)
      console.log("✅ Screen sharing stopped")
    } catch (error) {
      console.error("❌ Error stopping screen share:", error)
    }
  }

  const copyRoomId = () => {
    navigator.clipboard
      .writeText(roomId)
      .then(() => {
        alert("Room ID copied to clipboard!")
      })
      .catch(() => {
        // Fallback
        const textArea = document.createElement("textarea")
        textArea.value = roomId
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand("copy")
        document.body.removeChild(textArea)
        alert("Room ID copied to clipboard!")
      })
  }

  const leaveCall = () => {
    console.log("👋 Leaving call...")
    cleanup()
    onLeaveRoom()
  }

  const cleanup = () => {
    console.log("🧹 Cleaning up resources...")

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Stop all tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => {
        track.stop()
        console.log(`🛑 Stopped ${track.kind} track`)
      })
    }

    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach((track) => track.stop())
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close(1000, "User left")
    }

    // Close peer connections
    peerConnectionsRef.current.forEach((pc, userId) => {
      pc.close()
      console.log(`🔗 Closed peer connection for ${userId}`)
    })
    peerConnectionsRef.current.clear()

    // Clear state
    setRemoteStreams(new Map())
    setParticipants([])
    setLocalStream(null)
    setIsConnected(false)
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center max-w-lg p-6">
          <div className="bg-red-600 rounded-full p-4 w-16 h-16 mx-auto mb-4">
            <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">Connection Error</h2>
          <p className="text-gray-300 mb-4 whitespace-pre-line">{error}</p>
          <div className="space-y-2">
            <button onClick={initializeApp} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded mr-2">
              Try Again
            </button>
            <button onClick={leaveCall} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">
              Go Back
            </button>
          </div>

          {/* Helpful instructions */}
          <div className="mt-6 text-sm text-gray-400 bg-gray-800 p-4 rounded">
            <h3 className="font-bold mb-2">Troubleshooting:</h3>
            <div className="text-left space-y-1">
              <p>• Backend is hosted on Vercel: video-call-1-0-0.vercel.app</p>
              <p>• Check if the Vercel deployment is active</p>
              <p>• Vercel functions may have cold start delays</p>
              <p>• Check browser console for detailed error messages</p>
              <p>• Ensure camera/microphone permissions are granted</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold">Room: {roomId}</h1>
            <button
              onClick={copyRoomId}
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded border border-gray-600 transition duration-200"
            >
              <svg className="h-4 w-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              Copy ID
            </button>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`}></div>
              <span className="text-sm">{connectionStatus}</span>
            </div>
            <div className="flex items-center space-x-2">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
                />
              </svg>
              <span>{participants.length + 1} participants</span>
            </div>
          </div>
        </div>
      </header>

      {/* Video Grid */}
      <main className="flex-1 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
            {/* Local Video */}
            <ParticipantVideo
              participant={{
                id: "local",
                name: `${userName} (You)`,
                stream: localStream,
                audioEnabled: isAudioEnabled,
                videoEnabled: isVideoEnabled,
              }}
              isLocal={true}
              videoRef={localVideoRef}
            />

            {/* Remote participants */}
            {participants.map((participant) => (
              <ParticipantVideo
                key={participant.id}
                participant={{
                  ...participant,
                  stream: remoteStreams.get(participant.id),
                }}
                isLocal={false}
              />
            ))}
          </div>

          {/* Controls */}
          <VideoControls
            isAudioEnabled={isAudioEnabled}
            isVideoEnabled={isVideoEnabled}
            isScreenSharing={isScreenSharing}
            onToggleAudio={toggleAudio}
            onToggleVideo={toggleVideo}
            onToggleScreenShare={toggleScreenShare}
            onLeaveCall={leaveCall}
          />
        </div>
      </main>

      {/* Vercel Status */}
      <div className="fixed top-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400" : "bg-red-400"}`}></div>
          <div>
            <p className="font-bold text-sm">Vercel Backend</p>
            <p className="text-xs">video-call-1-0-0.vercel.app</p>
          </div>
        </div>
      </div>

      {/* Debug Info */}
      <div className="fixed bottom-4 left-4 bg-black bg-opacity-75 text-white p-3 rounded text-xs max-w-xs">
        <div className="font-bold mb-1">Debug Info:</div>
        <div>Backend: video-call-1-0-0.vercel.app</div>
        <div>WebSocket: wss://</div>
        <div>Server: {isConnected ? "✅ Connected" : "❌ Disconnected"}</div>
        <div>Local Stream: {localStream ? "✅ Active" : "❌ None"}</div>
        <div>Participants: {participants.length}</div>
        <div>Remote Streams: {remoteStreams.size}</div>
        <div>Peer Connections: {peerConnectionsRef.current.size}</div>
      </div>
    </div>
  )
}

export default VideoRoom
