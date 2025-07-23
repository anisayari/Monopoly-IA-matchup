const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-react']
          }
        }
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx']
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './public/index.html'
    })
  ],
  devServer: {
    static: {
      directory: path.join(__dirname, 'public'),
    },
    port: 3000,
    open: true,
    hot: true,
    setupMiddlewares: (middlewares, devServer) => {
      devServer.app.get('/api/game-logs', (req, res) => {
        const fs = require('fs');
        const logsPath = path.join(__dirname, '..', 'services', 'logs', 'game_logs.json');
        fs.readFile(logsPath, 'utf8', (err, data) => {
          if (err) {
            res.status(500).json({ error: 'Failed to read game logs' });
            return;
          }
          res.json(JSON.parse(data));
        });
      });
      return middlewares;
    }
  }
};