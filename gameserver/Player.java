import java.util.HashMap;
import java.util.Map;

public class Player {
    private GameServer gameServer;
    private long lastActionTime;
    private String playerName;
    private String currentRoom;
    private Map<String, Boolean> seenRooms;
    private String sid;

    public Player(GameServer gameServer, String sid, String playerName) {
        this.gameServer = gameServer;
        this.lastActionTime = System.currentTimeMillis();
        this.playerName = playerName;
        this.currentRoom = "Road";
        this.seenRooms = new HashMap<>();
        this.sid = sid;
        this.gameServer.registerPlayer(sid, this, playerName);
        this.gameServer.updatePlayerRoom(this.sid, this.currentRoom);
        String instructions = "Welcome to the game, " + playerName + ". "
            + this.gameServer.getPlayersText()
            + "Please input one of these commands:\n"
            + this.gameServer.getCommandsDescription();
        for (String line : instructions.split("\n")) {
            if (!line.isEmpty()) {
                this.gameServer.tellPlayer(this.sid, line, "instructions");
            }
        }
        this.gameServer.tellPlayer(sid, this.gameServer.getRoomDescription(this.currentRoom));
        this.seenRooms.put(this.currentRoom, true);
        this.gameServer.tellOthers(
            sid,
            playerName + " has joined the game, starting in the " + this.currentRoom + "; there are now " + this.gameServer.getPlayerCount() + " players.",
            true
        );
        this.gameServer.emitGameDataUpdate();
    }

    public void updateLastActionTime() {
        this.lastActionTime = System.currentTimeMillis();
    }

    public void moveToRoom(String nextRoom) {
        this.currentRoom = nextRoom;
        this.seenRooms.put(this.currentRoom, true);
    }

    public String getCurrentRoom() {
        return this.currentRoom;
    }
}