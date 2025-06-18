"use client"

const VideoControls = ({
  isAudioEnabled,
  isVideoEnabled,
  isScreenSharing,
  onToggleAudio,
  onToggleVideo,
  onToggleScreenShare,
  onLeaveCall,
}) => {
  return (
    <div className="flex justify-center items-center space-x-4 p-4 bg-gray-800 rounded-lg shadow-lg">
      {/* Audio Toggle */}
      <button
        onClick={onToggleAudio}
        className={`rounded-full w-14 h-14 flex items-center justify-center transition duration-200 ${
          isAudioEnabled ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-red-600 hover:bg-red-700 text-white"
        }`}
        title={isAudioEnabled ? "Mute microphone" : "Unmute microphone"}
      >
        {isAudioEnabled ? (
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        ) : (
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1m0 0V5a2 2 0 012-2h2a2 2 0 012 2v8.5M15 9.5a3 3 0 00-3-3V5a3 3 0 00-3 3v4a3 3 0 006 0v-.5z"
            />
          </svg>
        )}
      </button>

      {/* Video Toggle */}
      <button
        onClick={onToggleVideo}
        className={`rounded-full w-14 h-14 flex items-center justify-center transition duration-200 ${
          isVideoEnabled ? "bg-blue-600 hover:bg-blue-700 text-white" : "bg-red-600 hover:bg-red-700 text-white"
        }`}
        title={isVideoEnabled ? "Turn off camera" : "Turn on camera"}
      >
        {isVideoEnabled ? (
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        ) : (
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728"
            />
          </svg>
        )}
      </button>

      {/* Screen Share Toggle */}
      <button
        onClick={onToggleScreenShare}
        className={`rounded-full w-14 h-14 flex items-center justify-center transition duration-200 ${
          isScreenSharing
            ? "bg-green-600 hover:bg-green-700 text-white"
            : "bg-gray-600 hover:bg-gray-700 text-white border border-gray-500"
        }`}
        title={isScreenSharing ? "Stop screen sharing" : "Share screen"}
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      </button>

      {/* Settings Button */}
      <button
        className="bg-gray-600 hover:bg-gray-700 text-white rounded-full w-14 h-14 flex items-center justify-center border border-gray-500 transition duration-200"
        title="Settings"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Leave Call Button */}
      <button
        onClick={onLeaveCall}
        className="bg-red-600 hover:bg-red-700 text-white rounded-full w-14 h-14 flex items-center justify-center transition duration-200"
        title="Leave call"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 3l1.5 1.5M21 21l-1.5-1.5m0 0L3 3m16.5 16.5L21 21M12 18l.5-3.5-.5-3.5"
          />
        </svg>
      </button>
    </div>
  )
}

export default VideoControls
