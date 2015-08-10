/* -----------------------------------------------------------------------------
 * Copyright © 2015, Numenta, Inc. Unless you have purchased from
 * Numenta, Inc. a separate commercial license for this software code, the
 * following terms and conditions apply:
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 3 as published by
 * the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program. If not, see http://www.gnu.org/licenses.
 *
 * http://numenta.org/licenses/
 * -------------------------------------------------------------------------- */

'use strict';


/**
 * Gulp config
 * @flow
 */

// externals

import child from 'child_process';
import gulp from 'gulp';
import util from 'gulp-util';
import webpack from 'webpack';
import webpacker from 'webpack-stream';

const spawn = child.spawn;

// internals

import config from './package.json';

const HOST = process.env.TEST_HOST || 'http://localhost';
const PORT = process.env.TEST_PORT || 8008;
const PATH = process.env.TEST_PATH || '';

let WebServer = null; // @TODO not global


// Individual Tasks

/**
 * Gulp task to run mocha-casperjs web test suite
 */
gulp.task('mocha-casperjs', (callback) => {
  /*
  let stream = spawn('mocha-casperjs', [
    '--bail',
    '--TEST_HOST=' + HOST,
    '--TEST_PORT=' + PORT,
    '--TEST_PATH=' + PATH
  ]);

  console.log('Mocha-Casper: started. Output will follow soon...');

  stream.stdout.on('data', (data) => {
    process.stdout.write(data);
  });

  stream.on('close', (code) => {
    let success = code === 0; // Will be 1 in the event of failure

    if(WebServer) {
      WebServer.emit('kill');
      WebServer = null;
    }

    if(! success) {
      // fail
      callback(new Error('Mocha-Casper: failed!'));
      return;
    }

    // success
    console.log('Mocha-Casper: success!');
    callback();
  });

  stream.on('error', console.error);

  return stream;
  */
});

/**
 * Gulp task to serve site from the _site/ build dir
 */
gulp.task('serve', () => {
  /*
  let stream = gulp.src('.')
    .pipe(gwebserver({ port: PORT }))
    .on('error', console.error);

  WebServer = stream;

  return stream;
  */
});

/**
 * Gulp task to run WebPack to transpile require/modules/Babel into bundle
 */
gulp.task('webpack', ()  => {
  let target = util.env.target || 'web';
  return gulp.src('gui/browser/app.js')
    .pipe(webpacker({
      devtool: 'source-map',
      module: {
        loaders: [
          { test: /\.(js|jsx)$/, loader: 'babel-loader', exclude: /node_modules/ }
        ]
      },
      output: {
        filename: 'bundle.js'
      },
      plugins: [
        new webpack.IgnorePlugin(/vertx/)  // @TODO remove in fluxible 4.x
      ],
      resolve: {
        extensions: [ '', '.js', '.jsx' ]
      },
      target
    }))
    .pipe(gulp.dest('gui/browser/'));
});


// Task Compositions

gulp.task('default', []);
gulp.task('webtest', [ 'serve', 'mocha-casperjs' ]);
