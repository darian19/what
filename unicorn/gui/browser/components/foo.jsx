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
 * React View Component: Foo
 */

// externals

import Material from 'material-ui';
import React from 'react';

// internals

let LeftNav = Material.LeftNav;
let Theme = new Material.Styles.ThemeManager();

let menuItems = [
  { text: 'Get Started' },
  { text: 'Explore App' },
  { text: 'Send Feedback' }
];


// MAIN

/**
 *
 */
module.exports = React.createClass({
  /**
   *
   */
  childContextTypes: {
    muiTheme: React.PropTypes.object
  },

  /**
   *
   */
  getChildContext () {
    return {
      muiTheme: Theme.getCurrentTheme()
    };
  },

  /**
   *
   */
  render () {
    return (
      <div>
        <LeftNav ref="leftNav" menuItems={menuItems} />
        <h1>Welcome</h1>
        <p>{this.props.foo}</p>
      </div>
    );
  }
});
