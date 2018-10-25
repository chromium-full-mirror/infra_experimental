const path = require('path');

module.exports = {
  entry: ['./elements/mon-game.js'],
  devtool: 'inline-source-map',
  resolve: {
    extensions: [ '.js' ]
  },
  output: {
    filename: 'mon-game.js',
    path: path.resolve(__dirname, 'dist')
  }
};
