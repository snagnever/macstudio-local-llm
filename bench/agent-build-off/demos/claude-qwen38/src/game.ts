// Top-level state machine and frame loop. Owns the scene and every system.
// Order per frame: move world -> move player -> collide -> draw.

import { Scene, type Engine, type Mesh, type TransformNode } from "@babylonjs/core";
import { CameraRig } from "./cameraRig";
import { CFG } from "./config";
import { checkCollisions } from "./collision";
import { EventBus, type GameEventMap } from "./events";
import { Factory, type Entity } from "./factory";
import { Hud } from "./hud";
import { InputManager, type InputAction } from "./input";
import { Player } from "./player";
import { Powerups } from "./powerups";
import { Audio } from "./audio";
import { Score } from "./score";
import type { GameStateName } from "./state";
import { Track } from "./track";
import { World } from "./world";

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export class Game {
  private scene: Scene;
  private state: GameStateName = "menu";

  private time = 0; // total time since boot (drives animation phases)
  private elapsed = 0; // time inside the current run (drives difficulty)
  private difficulty = 0;
  private restartAt = 0; // game-over restart gate
  private wasGrounded = true;
  private hitEntity: Entity | null = null; // deferred hit (collision loop is iterating)

  private degraded = false;
  private fpsAvg = 60;
  private lowAcc = 0;

  private readonly bus = new EventBus<GameEventMap>();
  private readonly world: World;
  private readonly rig: CameraRig;
  private readonly factory: Factory;
  private readonly track: Track;
  private readonly player = new Player();
  private readonly score = new Score();
  private readonly powerups = new Powerups();
  private readonly audio = new Audio();
  private readonly hud: Hud;
  private readonly input: InputManager;
  private readonly ship: TransformNode;
  private readonly bubble: Mesh;

  constructor(private engine: Engine) {
    this.scene = new Scene(this.engine);

    this.world = new World(this.scene);
    this.rig = new CameraRig(this.scene);
    this.factory = new Factory(this.scene);
    this.track = new Track(this.factory);

    this.hud = new Hud(
      () => this.onAction("confirm"),
      () => this.toggleMute(),
    );
    this.hud.score = this.score;
    this.hud.powerups = this.powerups;
    this.hud.setMuted(this.audio.muted);

    this.ship = this.factory.buildShip();
    this.bubble = this.factory.buildShieldBubble();
    this.input = new InputManager((a) => this.onAction(a));

    this.bus.on("coin", () => {
      this.score.addCoin();
      this.audio.coin(this.score.combo);
    });
    this.bus.on("powerup", (kind) => {
      this.powerups.collect(kind);
      this.audio.pickup();
    });
    this.bus.on("launch", () => {
      this.player.launch(CFG.rampLaunchVy);
      this.audio.jump();
    });
    this.bus.on("hit", (entity) => {
      // Only record here. The collision loop is still walking `actives`;
      // releasing or resetting meshes mid-iteration would corrupt it.
      if (!this.hitEntity) this.hitEntity = entity;
    });

    // Attract mode: stock the track, show the menu.
    this.track.reset();
    this.hud.setState("menu");

    this.engine.runRenderLoop(() => this.frame());
  }

  private frame(): void {
    const dt = Math.min(this.engine.getDeltaTime() / 1000, CFG.maxDt);
    this.time += dt;

    // Auto-degrade glow when the frame rate stays below 45 fps.
    if (dt > 0) {
      this.fpsAvg = this.fpsAvg * 0.95 + (1 / dt) * 0.05;
      if (!this.degraded) {
        this.lowAcc = this.fpsAvg < 45 ? this.lowAcc + dt : 0;
        if (this.lowAcc > 2) {
          this.world.degradeGlow();
          this.degraded = true;
        }
      }
    }

    const playing = this.state === "playing";
    let speed: number = CFG.menuSpeed;
    if (playing) {
      this.elapsed += dt;
      this.difficulty = Math.min(
        1 - Math.exp(-this.elapsed / CFG.diffTau),
        CFG.diffCap,
      );
      speed =
        CFG.baseSpeed +
        (CFG.maxSpeed - CFG.baseSpeed) * this.difficulty +
        (this.powerups.active("boost") ? CFG.boostExtra : 0);
      this.audio.setDifficulty(this.difficulty);
    } else if (this.state === "gameover") {
      speed = 0; // freeze the world on death
    }

    this.track.setDifficulty(this.difficulty);
    this.track.update(dt, speed);
    this.factory.update(
      dt,
      speed,
      this.time,
      this.powerups.active("magnet"),
      this.player.x,
    );
    this.world.update(dt, speed, this.time);

    if (playing) {
      this.player.update(dt);
      if (!this.wasGrounded && this.player.grounded) this.audio.land();
      this.wasGrounded = this.player.grounded;

      this.score.update(dt, speed, this.powerups.active("boost"));
      this.powerups.update(dt);
      checkCollisions(this.factory, this.player, this.bus);

      const hit = this.hitEntity;
      if (hit) {
        this.hitEntity = null;
        if (this.powerups.consumeShield()) {
          this.audio.shieldBreak();
          this.rig.addShake(0.5);
          const idx = this.factory.actives.indexOf(hit);
          if (idx >= 0) this.factory.releaseAt(idx);
        } else {
          this.crash();
        }
      }
    }

    // Ship follows the player box; tilt from lane speed and vertical speed.
    this.ship.position.set(this.player.x, this.player.y, 0);
    this.ship.rotation.z = clamp(-this.player.vx * 0.02, -0.45, 0.45);
    this.ship.rotation.x = clamp(-this.player.vy * 0.012, -0.3, 0.3);
    this.ship.scaling.y = this.player.sliding ? 0.6 : 1;

    const shieldOn = playing && this.powerups.active("shield");
    this.bubble.isVisible = shieldOn;
    if (shieldOn) {
      this.bubble.position.set(this.player.x, this.player.y + 0.6, 0);
      const s = 1 + Math.sin(this.time * 6) * 0.05;
      this.bubble.scaling.setAll(s);
    }

    this.rig.update(
      dt,
      this.player.x,
      this.player.vx,
      playing && this.powerups.active("boost"),
      this.time,
    );

    this.scene.render();
  }

  private startRun(): void {
    this.player.reset();
    this.score.reset();
    this.powerups.reset();
    this.rig.reset();
    this.track.reset();
    this.elapsed = 0;
    this.difficulty = 0;
    this.wasGrounded = true;
    this.hitEntity = null;
    this.state = "playing";
    this.hud.setState("playing");
    this.audio.setDifficulty(0);
    this.audio.startMusic();
  }

  private crash(): void {
    this.state = "gameover";
    this.audio.crash();
    this.audio.gameOver();
    this.audio.stopMusic();
    this.rig.addShake(1.2);
    const record = this.score.submit();
    this.hud.showGameOver(this.score.display, this.score.best, record);
    this.hud.setState("gameover");
    this.restartAt = this.time + 0.6; // ignore instant re-triggers
  }

  private toggleMute(): void {
    this.audio.setMuted(!this.audio.muted);
    this.hud.setMuted(this.audio.muted);
  }

  private onAction(a: InputAction): void {
    // First gesture of the session; safe to call every time.
    this.audio.unlock();

    switch (this.state) {
      case "menu":
        if (a === "mute") this.toggleMute();
        else if (a === "confirm" || a === "tap" || a === "jump") {
          this.audio.ui();
          this.startRun();
        }
        break;

      case "playing":
        if (a === "left") {
          if (this.player.moveLane(-1)) this.audio.ui();
        } else if (a === "right") {
          if (this.player.moveLane(1)) this.audio.ui();
        } else if (a === "jump") {
          const before = this.player.vy;
          this.player.jump();
          if (this.player.vy !== before) this.audio.jump();
        } else if (a === "slide") {
          this.player.startSlide();
          this.audio.slide();
        } else if (a === "mute") {
          this.toggleMute();
        }
        break;

      case "gameover":
        if (a === "mute") this.toggleMute();
        else if (
          (a === "confirm" || a === "tap" || a === "jump") &&
          this.time >= this.restartAt
        ) {
          this.audio.ui();
          this.startRun();
        }
        break;
    }
  }
}
