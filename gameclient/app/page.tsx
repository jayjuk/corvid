"use client";
// ... (other imports)
import { useState, useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";
import styles from "./all_styles.module.css";

function useOrigin() {
  const [mounted, setMounted] = useState(false);
  const origin =
    typeof window !== "undefined" && window.location.origin
      ? window.location.origin
      : "";

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return origin;
}

function replaceAfterLastColon(
  input: string | null,
  replacement: string
): string {
  if (!input) return "";

  const lastIndex = input.lastIndexOf(":");

  if (lastIndex === -1) {
    return input; // No colon found in the string
  }

  return input.slice(0, lastIndex + 1) + replacement;
}

export default function HomePage() {
  const [gameLog, setGameLog] = useState<string[]>([]);
  const [userInput, setUserInput] = useState("");
  const [playerName, setPlayerName] = useState("");
  const [nameSet, setNameSet] = useState(false);
  const socket = useRef<Socket | null>(null);
  const originalHost: string | null = useOrigin();
  const gameServerHostName: string = replaceAfterLastColon(
    originalHost,
    "3001"
  );

  useEffect(() => {
    // Connect to the game server via socket.io
    // Socket.current = io("http://gameserver:3001");
    // TODO: make this dynamic, for now you need to add this to hosts file
    // when running outside of Azure : 127.0.0.1 jaysgame.westeurope.azurecontainer.io
    //socket.current = io("http://jaysgame.westeurope.azurecontainer.io:3001");
    socket.current = io(gameServerHostName);

    socket.current.on("game_update", (message) => {
      setGameLog((prevLog) => {
        const newLog = [...prevLog, message];
        // Keep only the last 10 messages
        return newLog.slice(-10);
      });
    });

    return () => {
      if (socket.current) {
        socket.current.disconnect();
      }
    };
  }, [gameServerHostName]);

  const handleNameSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (socket.current && playerName.trim() !== "") {
      socket.current.emit("set_player_name", playerName); // Emitting new event to the game engine
      setNameSet(true); // Name is now set, hide the input field
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (socket.current && userInput.trim() !== "") {
      socket.current.emit("user_action", userInput);
      setUserInput("");
    }
  };

  return (
    <div>
      <h1 style={{ textAlign: "center", margin: "20px 0" }}>
        A Simple Multiplayer Game
      </h1>
      {nameSet && (
        <h2 style={{ textAlign: "center", margin: "10px 0" }}>
          Player: {playerName}
        </h2>
      )}
      {!nameSet && ( // Conditionally rendering the name input field
        <form onSubmit={handleNameSubmit}>
          <input
            className={styles.inputField}
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Enter your name..."
          />
          <button type="submit">Set Name</button>
        </form>
      )}
      {nameSet && ( // Only rendering the output if user has input their name
        <div
          style={{
            overflowY: "auto",
            maxHeight: "400px",
            border: "1px solid gray",
          }}
        >
          {gameLog.map((entry, index) => (
            <div key={index}>{entry}</div>
          ))}
        </div>
      )}
      {nameSet && ( // Only rendering the user action field if user has input their name
        <form onSubmit={handleSubmit}>
          <input
            className={styles.inputField}
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Type your action..."
          />
          <button type="submit">Submit</button>
        </form>
      )}
    </div>
  );
}
