/**
 * @fileoverview Description of this file.
 */

let storage = window.localStorage

let MONSTERS = {
  "monorail": {
    "attack": 10,
    "description": "Best bug management in town",
    "health": 40,
    "image": "monorail2.png",
    "moves": [
      "tackle",
      "file_bug"
    ],
    "weight": 8.38
  },
  "logdog": {
    "attack": 10,
    "description": "Fiercest dog in town",
    "health": 40,
    "image": "logdog.png",
    "moves": [
      "bite",
      "tornado"
    ],
    "weight": 8.38
  },
  "swarming": {
    "attack": 10,
    "description": "The best scheduler around",
    "health": 40,
    "image": "swarming.png",
    "moves": [
      "sting",
      "tackle"
    ],
    "name": "swarming",
    "weight": 8.38
  }
};
//     "moves": {
//       "bite": {
//         "damage": 10
//       },
//       "file_bug": {
//         "damage": 10
//       },
//       "sting": {
//         "damage": 10
//       },
//       "tackle": {
//         "damage": 10
//       },
//       "tornado": {
//         "damage": 10
//       }
//     }
// };

function getOwnedMonsterNames() {
  var ownedMonsters = storage.getItem("ownedMonsters")
  if (ownedMonsters == null) {
    ownedMonsters = "monorail"
    storage.setItem("ownedMonsters", ownedMonsters);
  }
  return ownedMonsters.split(",");
}

export function getOwnedMonsters() {
  return getOwnedMonsterNames().map(x => Object.assign({}, MONSTERS[x], {name: x}));
}

function addCapturedMonster(monster) {
  var ownedMonsters = getOwnedMonsterNames();
  ownedMonsters = ownedMonsters + "," + monster;
  storage.setItem("ownedMonsters", ownedMonsters);
}
