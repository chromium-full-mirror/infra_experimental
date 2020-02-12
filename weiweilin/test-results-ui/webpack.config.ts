import path from 'path';
import webpack from 'webpack';

const config: webpack.Configuration = {
  mode: 'development',
  entry: './src/index.ts',
  output: {
    path: path.resolve(__dirname, 'static/dist/scripts'),
    filename: 'index.js'
  },
  module: {
    rules: [
      {
        enforce: 'pre',
        test: /\.css$/,
        use: [
          'to-string-loader',
          // "@teamsupercell/typings-for-css-modules-loader",
          {
            loader: 'css-loader',
          }
        ],
      },
      {
        test: /\.ts$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.css', '.js', '.ts'],
  },
  resolveLoader: {
    modules: [
      'node_modules',
      path.resolve(__dirname, './loaders'),
    ]
  },
  plugins: [
  ],
  devServer: {
    contentBase: path.join(__dirname, 'public'),
    publicPath: '/dist/scripts/',
    historyApiFallback: true,
  }
};

export default config;
