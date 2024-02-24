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
  const [roomImageURL, setRoomImageURL] = useState(null);
  const [roomTitle, setRoomTitle] = useState(null);
  const [roomDescription, setRoomDescription] = useState(null);
  const [roomExits, setRoomExits] = useState(null);
  const socket = useRef<Socket | null>(null);
  const originalHost: string | null = useOrigin();
  const gameServerHostName: string = replaceAfterLastColon(
    originalHost,
    "3001"
  );
  const gameLogRef = useRef<HTMLDivElement>(null);
  // Add a state variable to keep track of the previous commands
  const [previousCommands, setPreviousCommands] = useState<string[]>([]);
  const [commandIndex, setCommandIndex] = useState<number>(0);

  useEffect(() => {
    // Connect to the game server via socket.io
    socket.current = io(gameServerHostName);

    // Instructions come on their own and should be simply displayed.
    socket.current.on("instructions", (instructions) => {
      setGameLog((prevLog) => {
        const newLog = [...prevLog, instructions];
        return newLog;
      });
    });

    socket.current.on("game_update", (message) => {
      // Strip curly brackets (indicate content to be hidden from models)
      message = message.replace(/[{|}]/g, "");
      setGameLog((prevLog) => {
        const newLog = [...prevLog, message];
        // Keep only the last 10 messages
        return newLog.slice(-10);
      });
    });

    // Listen for the room update event from the server
    socket.current.on("room_update", (message) => {
      setRoomImageURL(message["image"]);
      setRoomTitle(message["title"]);
      //Strip curly backets out (they tell the AI broker what is superfluous to the LLM)
      setRoomDescription(message["description"].replace(/[{|}]/g, ""));
      setRoomExits(message["exits"]);
    });

    // Listen for the 'shutdown' event from the server
    socket.current.on("shutdown", (message) => {
      if (message != null) {
        message = "The server is shutting down!"
      }
      console.log(message);
      alert(message);
      setNameSet(false);
    });

    // Listen for the 'logout' event from the server
    socket.current.on("logout", (message) => {
      console.log("Logging out");
      if (message != null) {
        alert(message);
      }
      setNameSet(false);
    });

    return () => {
      if (socket.current) {
        socket.current.disconnect();
      }
    };
  }, [gameServerHostName]);

  // Scroll to the bottom of the game log whenever it changes
  useEffect(() => {
    if (gameLogRef.current) {
      gameLogRef.current.scrollTop = gameLogRef.current.scrollHeight;
    }
  }, [gameLog]);

  const handleNameSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (socket.current && playerName.trim() !== "") {
      socket.current.emit("set_player_name", { name: playerName }); // Emitting new event to the game engine
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

  // Modify your onChange handler to store the user input as a previous command
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUserInput(e.target.value);
    setPreviousCommands(prevCommands => [...prevCommands, e.target.value]);
    setCommandIndex(0);
  };

    // Add a keyUp handler to handle the up arrow key
  const handleKeyUp = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp' && commandIndex < previousCommands.length) {
      setUserInput(previousCommands[previousCommands.length - 1 - commandIndex]);
      setCommandIndex(prevIndex => prevIndex + 1);
    }
  };

  // Add a keyDown handler to handle the up arrow key
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && commandIndex > 0) {
      setUserInput(previousCommands[previousCommands.length - commandIndex]);
      setCommandIndex(prevIndex => prevIndex - 1);
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
            autoFocus
          />
          <button type="submit">Set Name</button>
        </form>
      )}
      {nameSet && roomImageURL && (
        <div style={{ display: "flex", flexDirection: "row" }}>
          <img src={roomImageURL ?? ""} alt={roomTitle ?? ""} width="512" />
          {/* Some text to the right of the image */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              marginLeft: "10px",
            }}
          >
            <p style={{ margin: 0, maxWidth: 1000 }}>
              <b>{roomTitle}</b>: {roomDescription} {roomExits}
            </p>
          </div>
        </div>
      )}
      {nameSet && ( // Only rendering the output if user has input their name
        <>
          <div
            ref={gameLogRef}
            style={{
              overflowY: "auto",
              minHeight: "300px",
              maxHeight: "400px",
              border: "1px solid gray",
            }}
          >
            {gameLog.map((entry, index) => (
              <div key={index}>{entry}</div>
            ))}
          </div>
          <form onSubmit={handleSubmit}>
            <input
              className={styles.inputField}
              type="text"
              value={userInput}
              onChange={handleInputChange}
              onKeyUp={handleKeyUp}
              onKeyDown={handleKeyDown}
              placeholder="Type your action..."
              autoFocus
            />
            <button type="submit">Submit</button>
          </form>
        </>
      )}
    </div>
  );
}
