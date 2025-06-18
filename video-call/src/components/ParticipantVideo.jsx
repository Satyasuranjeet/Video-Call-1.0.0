"use client"

import { useEffect, useRef } from "react"

const ParticipantVideo = ({ participant, isLocal = false, videoRef }) => {
  const internalVideoRef = useRef(null)
  const currentVideoRef = videoRef || internalVideoRef

  useEffect(() => {
    if (currentVideoRef.current && participant.stream) {
      console.log(`🎬 Setting video stream for ${participant.name}`)
      currentVideoRef.current.srcObject = participant.stream

      // Ensure video plays
      currentVideoRef.current.play().catch((error) => {
        console.log("Video autoplay prevented:", error)
      })
    }
  }, [participant.stream, currentVideoRef, participant.name])

  const hasVideo = participant.stream && participant.videoEnabled !== false
  const hasAudio = participant.audioEnabled !== false

  return (
    <div className="relative bg-gray-800 border-2 border-gray-700 overflow-hidden aspect-video rounded-lg shadow-lg hover:border-blue-500 transition-all duration-200">
      {hasVideo ? (
        <video
          ref={currentVideoRef}
          autoPlay
          muted={isLocal}
          playsInline
          className="w-full h-full object-cover"
          onLoadedMetadata={() => {
            console.log(`✅ Video loaded for ${participant.name}`)
          }}
          onError={(e) => {
            console.error(`❌ Video error for ${participant.name}:`, e)
          }}
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-800 flex flex-col items-center justify-center">
          <div className="bg-gray-600 rounded-full p-6 mb-3 shadow-lg">
            <svg className="h-16 w-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
              />
            </svg>
          </div>
          <p className="text-gray-300 text-sm font-medium">Camera off</p>
        </div>
      )}

      {/* Participant name overlay */}
      <div className="absolute bottom-3 left-3 bg-black bg-opacity-75 px-3 py-1 rounded-full">
        <span className="text-white text-sm font-medium">{participant.name}</span>
      </div>

      {/* Audio muted indicator */}
      {!hasAudio && (
        <div className="absolute top-3 right-3 bg-red-600 rounded-full p-2 shadow-lg">
          <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1m0 0V5a2 2 0 012-2h2a2 2 0 012 2v8.5M15 9.5a3 3 0 00-3-3V5a3 3 0 00-3 3v4a3 3 0 006 0v-.5z"
            />
          </svg>
        </div>
      )}

      {/* Connection status for remote participants */}
      {!isLocal && !participant.stream && (
        <div className="absolute top-3 left-3 bg-yellow-600 px-3 py-1 rounded-full">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
            <span className="text-white text-xs font-medium">Connecting...</span>
          </div>
        </div>
      )}

      {/* Video quality indicator */}
      {hasVideo && (
        <div className="absolute top-3 left-3 bg-green-600 px-2 py-1 rounded text-xs text-white font-medium opacity-75">
          HD
        </div>
      )}
    </div>
  )
}

export default ParticipantVideo
