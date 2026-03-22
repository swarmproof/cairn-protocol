#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Read the compiled contract
const contractPath = path.join(__dirname, '../../contracts/out/CairnCore.sol/CairnCore.json');
const abiOutputPath = path.join(__dirname, '../abis/CairnCore.json');

const compiledContract = JSON.parse(fs.readFileSync(contractPath, 'utf8'));
const abi = compiledContract.abi;

// Write just the ABI
fs.writeFileSync(abiOutputPath, JSON.stringify(abi, null, 2));

console.log('ABI extracted successfully to', abiOutputPath);
