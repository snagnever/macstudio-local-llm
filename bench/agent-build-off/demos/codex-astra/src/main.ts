import './style.css';
import { Game } from './game/Game';

const game = new Game(document.querySelector<HTMLCanvasElement>('#game')!, document.querySelector<HTMLElement>('#app')!);
void game.init();
if (import.meta.hot) import.meta.hot.dispose(() => game.dispose());
window.addEventListener('pagehide', event => { if (!event.persisted) game.dispose(); });
