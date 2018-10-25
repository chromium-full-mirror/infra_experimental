export function randInt(max, min) {
  min = min || 0;
  return Math.floor(Math.random() * (max - min)) + min;
}

export function arrayChoice(arr) {
  return arr[randInt(arr.length)];
}

export function sleep(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds))
}
