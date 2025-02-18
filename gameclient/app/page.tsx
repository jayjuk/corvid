"use client";
import { useState, useEffect, useRef } from "react";
import { connect, StringCodec, NatsConnection } from "nats.ws";
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
  const natsConnection = useRef<NatsConnection | null>(null);
  const originalHost: string | null = useOrigin();
  const strippedHost: string | null = originalHost?.replace(/^https?:\/\//, "") ?? null; // Strip http:// or https://
  const gameServerHostName: string = replaceAfterLastColon(
    strippedHost,
    "9222"
  );
  const gameLogRef = useRef<HTMLDivElement>(null);
  const [previousCommands, setPreviousCommands] = useState<string[]>([]);
  const [commandIndex, setCommandIndex] = useState<number>(0);
  const isConnected = useRef(false); // Add a flag to track connection status

  useEffect(() => {
  const connectToNats = async () => {
    if (natsConnection.current || !gameServerHostName) return; // Prevent multiple connections

    try {
      console.log(`Connecting to NATS at ws://${gameServerHostName}`);
      const nc = await connect({ servers: `ws://${gameServerHostName}` });
      natsConnection.current = nc;

    } catch (error) {
      console.error("Failed to connect to NATS:", error);
    }
  };

  connectToNats();

  return () => {
    if (natsConnection.current) {
      console.log("Closing NATS connection...");
      natsConnection.current.close();
      natsConnection.current = null;
    }
  };
}, [gameServerHostName]); // Only runs once when gameServerHostName is set


useEffect(() => {
  if (!playerName || !natsConnection.current) return; // Wait until playerName is set

  const nc = natsConnection.current;
  const sc = StringCodec();

    // Function to handle game updates
  const handleGameUpdate = async (sub: any) => {
    for await (const msg of sub) {
      let message = sc.decode(msg.data).replace(/[{|}]/g, "");
      setGameLog((prevLog) => {
        const newLog = [...prevLog, message];
        return newLog.slice(-10);
      });
    }
  };

  // Subscribe to game updates
  handleGameUpdate(natsConnection.current.subscribe("game_update"));

  console.log(`Subscribing to player-specific topics for ${playerName}`);

    // Subscribe to player-specific game updates
  if (playerName) {
    handleGameUpdate(natsConnection.current.subscribe(`game_update.${playerName}`));
  }

  // Subscribe to player-specific instructions
  const instructionSub = nc.subscribe(`instructions.${playerName}`);
  (async () => {
    for await (const msg of instructionSub) {
      setGameLog((prev) => [...prev, sc.decode(msg.data)]);
    }
  })();

  // Subscribe to room updates
  const roomSub = nc.subscribe(`room_update.${playerName}`);
  (async () => {
    for await (const msg of roomSub) {
      const message = JSON.parse(sc.decode(msg.data));
      setRoomImageURL(message["image"]);
      setRoomTitle(message["title"]);
      setRoomDescription(message["description"].replace(/[{|}]/g, ""));
      setRoomExits(message["exits"]);
    }
  })();

  return () => {
    instructionSub.unsubscribe();
    roomSub.unsubscribe();
  };
}, [nameSet]); // Only runs when playerName is set/changes



  useEffect(() => {
    if (gameLogRef.current) {
      gameLogRef.current.scrollTop = gameLogRef.current.scrollHeight;
    }
  }, [gameLog]);

  const handleNameSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (natsConnection.current && playerName.trim() !== "") {
      const sc = StringCodec();
      natsConnection.current.publish("set_player_name", sc.encode(JSON.stringify({ name: playerName })));
      setNameSet(true);
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (natsConnection.current && userInput.trim() !== "") {
      const sc = StringCodec();
      const message = {
        player_id: playerName, // Use playerName as the player ID
        player_input: userInput,
      };
      natsConnection.current.publish("user_action", sc.encode(JSON.stringify(message)));
      setUserInput("");
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUserInput(e.target.value);
    setPreviousCommands((prevCommands) => [...prevCommands, e.target.value]);
    setCommandIndex(0);
  };

  const handleKeyUp = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowUp" && commandIndex < previousCommands.length) {
      setUserInput(previousCommands[previousCommands.length - 1 - commandIndex]);
      setCommandIndex((prevIndex) => prevIndex + 1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && commandIndex > 0) {
      setUserInput(previousCommands[previousCommands.length - commandIndex]);
      setCommandIndex((prevIndex) => prevIndex - 1);
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
      {!nameSet && (
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
      {nameSet && (
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