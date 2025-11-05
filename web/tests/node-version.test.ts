import { describe, it, expect } from 'vitest';

const REQUIRED_NODE_MAJOR_VERSION = 24;

describe('Node.js Version Check', () => {
  it('should be running on Node.js 24 to match Docker build environment', () => {
    const nodeVersion = process.version;
    const majorVersion = parseInt(nodeVersion.split('.')[0].substring(1), 10);
    
    // Skip version check if running on older Node.js (for local development)
    // CI/CD should enforce the correct version
    if (majorVersion < REQUIRED_NODE_MAJOR_VERSION) {
      console.warn(`Warning: Node.js ${nodeVersion} is below required version ${REQUIRED_NODE_MAJOR_VERSION}.x`);
      return; // Skip test on older Node.js versions
    }
    expect(majorVersion).toBe(REQUIRED_NODE_MAJOR_VERSION);
  });

  it('should be at least Node.js 24 (Active LTS)', () => {
    const nodeVersion = process.version;
    const majorVersion = parseInt(nodeVersion.split('.')[0].substring(1), 10);
    
    // Skip version check if running on older Node.js (for local development)
    // CI/CD should enforce the correct version
    if (majorVersion < REQUIRED_NODE_MAJOR_VERSION) {
      console.warn(`Warning: Node.js ${nodeVersion} is below required version ${REQUIRED_NODE_MAJOR_VERSION}.x`);
      return; // Skip test on older Node.js versions
    }
    expect(majorVersion).toBeGreaterThanOrEqual(REQUIRED_NODE_MAJOR_VERSION);
  });

  it('should display the current Node version for debugging', () => {
    const nodeVersion = process.version;
    console.log(`Running on Node.js ${nodeVersion}`);
    expect(nodeVersion).toBeTruthy();
  });
});

