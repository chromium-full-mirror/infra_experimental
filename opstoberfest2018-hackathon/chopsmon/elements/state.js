import { MONSTERS } from '../data/monsters.js';
import { arrayChoice } from './helpers.js';

let storage = window.localStorage;

function processMonster(mon) {
  mon.maxHealth = mon.health;
  return mon;
}

export const MONSTERS_MAP = MONSTERS.reduce(
  (acc, v) => Object.assign({}, acc, {[v.name]: processMonster(v)}),
  {});

export function getOwnedMonsterNames() {
  let ownedMonsters = storage.getItem("ownedMonsters");
  if (ownedMonsters == null) {
    ownedMonsters = "monorail";
    storage.setItem("ownedMonsters", ownedMonsters);
  }
  return ownedMonsters.split(",");
}

export function getOwnedMonsters() {
  return getOwnedMonsterNames().map(x => Object.assign({}, MONSTERS_MAP[x]));
}

export function addCapturedMonster(monster) {
  let ownedMonsters = getOwnedMonsterNames();
  ownedMonsters = ownedMonsters + "," + monster;
  storage.setItem("ownedMonsters", ownedMonsters);
}

export function getActiveMonster() {
  const ownedMonsters = getOwnedMonsterNames();
  let activeMonster = storage.getItem("activeMonster");
  if (!ownedMonsters.includes(activeMonster)) {
    activeMonster = arrayChoice(ownedMonsters);
    storage.setItem("activeMonster", activeMonster);
  }
  return Object.assign({}, MONSTERS_MAP[activeMonster]);
}

export function setActiveMonster(monster) {
  const ownedMonsters = getOwnedMonsterNames();
  if (ownedMonsters.includes(monster)) {
    storage.setItem("activeMonster", monster);
  }
}
