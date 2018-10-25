import { MONSTERS } from '../data/monsters.js';

let storage = window.localStorage;

export const MONSTERS_MAP = MONSTERS.reduce(
  (acc, v) => Object.assign({}, acc, {[v.name]: v}),
  {});

export function getOwnedMonsterNames() {
  var ownedMonsters = storage.getItem("ownedMonsters")
  if (ownedMonsters == null) {
    ownedMonsters = "monorail"
    storage.setItem("ownedMonsters", ownedMonsters);
  }
  return ownedMonsters.split(",");
}

export function getOwnedMonsters() {
  return getOwnedMonsterNames().map(x => Object.assign({}, MONSTERS_MAP[x], {name: x}));
}

export function addCapturedMonster(monster) {
  var ownedMonsters = getOwnedMonsterNames();
  ownedMonsters = ownedMonsters + "," + monster;
  storage.setItem("ownedMonsters", ownedMonsters);
}
