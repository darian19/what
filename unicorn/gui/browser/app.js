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
 * Unicorn: Cross-platform Desktop Application to showcase basic HTM features
 *  to a user using their own data stream or files.
 *
 * Main browser web code Application GUI entry point.
 */

// externals

import Fluxible from 'fluxible';
import FluxibleReact from 'fluxible-addons-react';
import React from 'react';
import tapEventInject from 'react-tap-event-plugin';

// internals

import FooAction from './actions/foo';
import FooComponent from './components/foo';
import FooStore from './stores/foo';

let FooView = FluxibleReact.provideContext(
  FluxibleReact.connectToStores(
    FooComponent,
    [ FooStore ],
    (context, props) => {
      return context.getStore(FooStore).getState();
    }
  )
);


// MAIN

window.React = React; // dev tools @TODO remove for non-dev

tapEventInject(); // remove when >= React 1.0

// create fluxible app
let app = new Fluxible({
  component:  FooComponent,
  stores:     [ FooStore ]
});

// add context to app
let context = app.createContext();

// fire initial action
context.executeAction(FooAction, 'bar', (err) => {
  let output = React.renderToString(
    FluxibleReact.createElementWithContext(context)
  );

  console.log(output);
  if(document) document.write(output);
});
