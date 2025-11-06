#!/usr/bin/env node

/**
 * Generate open source attribution data from npm and pip dependencies.
 * This script extracts license information and creates a JSON file
 * that can be consumed by the Attributions page.
 */

import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

/**
 * Extract license information from package-lock.json
 * Handles various license formats: string, object, array
 */
function extractLicense(licenseField) {
  if (!licenseField) return 'Unknown';
  
  if (typeof licenseField === 'string') {
    return licenseField;
  }
  
  if (typeof licenseField === 'object') {
    // Could be { type: "MIT" } or { type: "MIT", url: "..." }
    if (licenseField.type) {
      return licenseField.type;
    }
    // Could be an array: [{ type: "MIT" }, { type: "Apache-2.0" }]
    if (Array.isArray(licenseField)) {
      return licenseField.map(l => typeof l === 'string' ? l : (l.type || 'Unknown')).join(' OR ');
    }
  }
  
  return 'Unknown';
}

/**
 * Parse package.json and package-lock.json to extract npm dependencies
 * Uses license-checker if available for more accurate license info
 */
function getNpmDependencies() {
  try {
    // Try to use license-checker first (more accurate)
    try {
      const output = execSync('npx --yes license-checker --json --start .', {
        encoding: 'utf-8',
        cwd: __dirname,
        stdio: ['ignore', 'pipe', 'ignore']
      });
      
      const licenseData = JSON.parse(output);
      const dependencies = [];
      
      for (const [packagePath, info] of Object.entries(licenseData)) {
        // Skip root package
        if (packagePath === '.') continue;
        
        // Extract package name (handle scoped packages)
        const nameMatch = packagePath.match(/^(.+?)@(.+)$/);
        if (!nameMatch) continue;
        
        const name = nameMatch[1];
        const version = nameMatch[2];
        
        // license-checker provides licenses as a string, sometimes comma-separated
        const license = info.licenses || info.license || 'Unknown';
        const repository = info.repository || info.url || `https://www.npmjs.com/package/${name}`;
        const author = info.publisher || info.author || 'Unknown';
        
        dependencies.push({
          name,
          version,
          license: typeof license === 'string' ? license : extractLicense(license),
          repository: typeof repository === 'string' ? repository : (repository?.url || `https://www.npmjs.com/package/${name}`),
          author: typeof author === 'string' ? author : (author?.name || 'Unknown'),
          description: info.description || '',
          type: 'npm'
        });
      }
      
      return dependencies.sort((a, b) => a.name.localeCompare(b.name));
    } catch (licenseCheckerError) {
      // Fallback to parsing package-lock.json manually
      console.warn('license-checker not available, parsing package-lock.json directly');
      
      const packageJsonPath = join(__dirname, 'package.json');
      const packageLockPath = join(__dirname, 'package-lock.json');
      
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
      const packageLock = JSON.parse(readFileSync(packageLockPath, 'utf-8'));
      
      const dependencies = [];
      const allDeps = { ...packageJson.dependencies, ...packageJson.devDependencies };
      
      // Extract license info from package-lock.json
      const packages = packageLock.packages || {};
      
      for (const [name, version] of Object.entries(allDeps)) {
        const packageKey = `node_modules/${name}`;
        const lockInfo = packages[packageKey] || packages[name];
        
        if (lockInfo) {
          const license = extractLicense(lockInfo.license);
          
          // Try to get repository URL
          let repository = `https://www.npmjs.com/package/${name}`;
          if (lockInfo.repository) {
            repository = typeof lockInfo.repository === 'string' 
              ? lockInfo.repository 
              : (lockInfo.repository.url || repository);
          } else if (lockInfo.homepage) {
            repository = lockInfo.homepage;
          }
          
          // Normalize repository URL
          if (repository.startsWith('git+')) {
            repository = repository.replace(/^git\+/, '').replace(/\.git$/, '');
          }
          
          dependencies.push({
            name,
            version: version.replace(/[\^~]/, ''),
            license,
            repository,
            author: lockInfo.author?.name || (typeof lockInfo.author === 'string' ? lockInfo.author : 'Unknown') || 'Unknown',
            description: lockInfo.description || '',
            type: 'npm'
          });
        } else {
          // Fallback if not in lock file
          dependencies.push({
            name,
            version: version.replace(/[\^~]/, ''),
            license: 'Unknown',
            repository: `https://www.npmjs.com/package/${name}`,
            author: 'Unknown',
            description: '',
            type: 'npm'
          });
        }
      }
      
      return dependencies.sort((a, b) => a.name.localeCompare(b.name));
    }
  } catch (error) {
    console.error('Error reading npm dependencies:', error.message);
    return [];
  }
}

/**
 * Parse requirements.txt to extract Python dependencies
 * Note: This is a basic implementation. For full license info,
 * you may want to use pip-licenses tool.
 */
function getPythonDependencies() {
  try {
    const requirementsPath = join(rootDir, 'requirements.txt');
    const requirementsDevPath = join(rootDir, 'requirements-dev.txt');
    
    const dependencies = [];
    
    function parseRequirements(filePath) {
      try {
        const content = readFileSync(filePath, 'utf-8');
        const lines = content.split('\n');
        
        for (const line of lines) {
          const trimmed = line.trim();
          // Skip comments, empty lines, and include directives (-r, --requirement, etc.)
          if (!trimmed || 
              trimmed.startsWith('#') || 
              trimmed.startsWith('-r') || 
              trimmed.startsWith('--requirement') ||
              trimmed.startsWith('--index-url') ||
              trimmed.startsWith('--extra-index-url') ||
              trimmed.startsWith('--find-links') ||
              trimmed.startsWith('--no-index') ||
              trimmed.startsWith('--pre') ||
              trimmed.startsWith('--trusted-host')) {
            continue;
          }
          
          // Parse package name and version
          // Format: package==version or package>=version, etc.
          const match = trimmed.match(/^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)([=<>!]+)?(.+)?$/);
          if (match) {
            const name = match[1].split('[')[0]; // Remove extras like [email]
            const version = match[3] || 'Unknown';
            
            // Skip if name is empty or looks like a flag/option
            if (!name || name.startsWith('-')) {
              continue;
            }
            
            dependencies.push({
              name,
              version: version.trim(),
              license: 'Unknown', // Would need pip-licenses for accurate data
              repository: `https://pypi.org/project/${name}/`,
              author: 'Unknown',
              description: '',
              type: 'python'
            });
          }
        }
      } catch (error) {
        // File might not exist, that's okay
        if (error.code !== 'ENOENT') {
          console.warn(`Warning reading ${filePath}:`, error.message);
        }
      }
    }
    
    parseRequirements(requirementsPath);
    parseRequirements(requirementsDevPath);
    
    return dependencies.sort((a, b) => a.name.localeCompare(b.name));
  } catch (error) {
    console.error('Error reading Python dependencies:', error.message);
    return [];
  }
}

/**
 * Try to use pip-licenses if available to get better license info
 * pip-licenses is much more accurate than parsing requirements.txt
 */
function enhancePythonLicenses(dependencies) {
  try {
    // Try to run pip-licenses if available
    // Use --with-authors and --with-urls for complete info
    const output = execSync('pip-licenses --format=json --with-urls --with-authors --with-description', {
      encoding: 'utf-8',
      cwd: rootDir,
      stdio: ['ignore', 'pipe', 'ignore']
    });
    
    const licenseData = JSON.parse(output);
    const licenseMap = {};
    
    for (const pkg of licenseData) {
      const name = pkg.Name.toLowerCase();
      licenseMap[name] = {
        license: pkg.License || 'Unknown',
        author: pkg.Author || 'Unknown',
        url: pkg.URL || `https://pypi.org/project/${pkg.Name}/`,
        version: pkg.Version || 'Unknown',
        description: pkg.Description || ''
      };
    }
    
    // Enhance dependencies with license info
    return dependencies.map(dep => {
      const enhanced = licenseMap[dep.name.toLowerCase()];
      if (enhanced) {
        return {
          ...dep,
          license: enhanced.license,
          author: enhanced.author,
          repository: enhanced.url,
          version: enhanced.version !== 'Unknown' ? enhanced.version : dep.version,
          description: enhanced.description || dep.description
        };
      }
      return dep;
    });
  } catch (error) {
    // pip-licenses not available or failed, return as-is
    console.warn('⚠️  pip-licenses not available, using basic license info');
    console.warn('   Install with: pip install pip-licenses');
    return dependencies;
  }
}

/**
 * Main function to generate attribution data
 */
function generateAttributions() {
  console.log('📦 Generating open source attributions...');
  
  const npmDeps = getNpmDependencies();
  console.log(`  Found ${npmDeps.length} npm dependencies`);
  
  let pythonDeps = getPythonDependencies();
  console.log(`  Found ${pythonDeps.length} Python dependencies`);
  
  // Try to enhance Python dependencies with pip-licenses
  pythonDeps = enhancePythonLicenses(pythonDeps);
  
  const attributions = {
    generatedAt: new Date().toISOString(),
    npm: npmDeps,
    python: pythonDeps,
    summary: {
      total: npmDeps.length + pythonDeps.length,
      npm: npmDeps.length,
      python: pythonDeps.length
    }
  };
  
  const outputPath = join(__dirname, 'public', 'attributions.json');
  writeFileSync(outputPath, JSON.stringify(attributions, null, 2));
  
  console.log('✅ Attributions generated:', outputPath);
  console.log(`   Total packages: ${attributions.summary.total}`);
  
  return attributions;
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  generateAttributions();
}

export { generateAttributions };

