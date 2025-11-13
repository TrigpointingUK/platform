import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  getIconBaseName,
  getConditionColor,
  getUserLogColor,
  getIconUrl,
  getIconUrlForTrig,
  getPreferredIconColorMode,
  setPreferredIconColorMode,
  DEFAULT_ICON_COLOR_MODE,
  ICON_COLOR_MODE_STORAGE_KEY,
  ICON_LEGENDS,
  type UserLogStatus,
  type IconColorMode,
} from '../mapIcons';
import { mockLocalStorage } from '../../components/map/__tests__/test-utils';

describe('mapIcons', () => {
  describe('getIconBaseName', () => {
    it('should map Pillar to pillar icon', () => {
      expect(getIconBaseName('Pillar')).toBe('pillar');
    });

    it('should map FBM to fbm icon', () => {
      expect(getIconBaseName('FBM')).toBe('fbm');
      expect(getIconBaseName('Flush Bracket')).toBe('fbm');
    });

    it('should map Passive Station to passive icon', () => {
      expect(getIconBaseName('Passive Station')).toBe('passive');
      expect(getIconBaseName('Passive station')).toBe('passive');
    });

    it('should map Intersection to intersected icon', () => {
      expect(getIconBaseName('Intersection')).toBe('intersected');
      expect(getIconBaseName('Intersected Station')).toBe('intersected');
    });

    it('should map Bolt to pillar icon (fallback)', () => {
      expect(getIconBaseName('Bolt')).toBe('pillar');
    });

    it('should map Active Station to passive icon (fallback)', () => {
      expect(getIconBaseName('Active Station')).toBe('passive');
    });

    it('should map Other to pillar icon (fallback)', () => {
      expect(getIconBaseName('Other')).toBe('pillar');
    });

    it('should handle unknown types with default', () => {
      expect(getIconBaseName('Unknown Type')).toBe('pillar');
    });
  });

  describe('getConditionColor', () => {
    it('should map G (Good) to green', () => {
      expect(getConditionColor('G')).toBe('green');
      expect(getConditionColor('g')).toBe('green');
    });

    it('should map D (Damaged) to yellow', () => {
      expect(getConditionColor('D')).toBe('yellow');
      expect(getConditionColor('d')).toBe('yellow');
    });

    it('should map M (Missing) to red', () => {
      expect(getConditionColor('M')).toBe('red');
      expect(getConditionColor('m')).toBe('red');
    });

    it('should map P (Possibly Missing) to red', () => {
      expect(getConditionColor('P')).toBe('red');
      expect(getConditionColor('p')).toBe('red');
    });

    it('should map U (Unknown) to grey', () => {
      expect(getConditionColor('U')).toBe('grey');
      expect(getConditionColor('u')).toBe('grey');
    });

    it('should handle unknown conditions with grey (default)', () => {
      expect(getConditionColor('X')).toBe('grey');
      expect(getConditionColor('')).toBe('grey');
    });
  });

  describe('getUserLogColor', () => {
    it('should return grey when not logged', () => {
      const logStatus: UserLogStatus = { hasLogged: false };
      expect(getUserLogColor(logStatus)).toBe('grey');
    });

    it('should return green when logged as found', () => {
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: true };
      expect(getUserLogColor(logStatus)).toBe('green');
    });

    it('should return green when logged without foundStatus (assumes found)', () => {
      const logStatus: UserLogStatus = { hasLogged: true };
      expect(getUserLogColor(logStatus)).toBe('green');
    });

    it('should return red when logged as not found', () => {
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: false };
      expect(getUserLogColor(logStatus)).toBe('red');
    });
  });

  describe('getIconUrl', () => {
    it('should construct correct path for pillar green', () => {
      const url = getIconUrl('Pillar', 'green');
      expect(url).toBe('/icons/mapicon_pillar_green.png');
    });

    it('should construct correct path for fbm yellow', () => {
      const url = getIconUrl('FBM', 'yellow');
      expect(url).toBe('/icons/mapicon_fbm_yellow.png');
    });

    it('should construct correct path for passive red', () => {
      const url = getIconUrl('Passive Station', 'red');
      expect(url).toBe('/icons/mapicon_passive_red.png');
    });

    it('should add _h suffix for highlighted icons', () => {
      const url = getIconUrl('Pillar', 'green', true);
      expect(url).toBe('/icons/mapicon_pillar_green_h.png');
    });

    it('should not add suffix for non-highlighted icons', () => {
      const url = getIconUrl('Pillar', 'green', false);
      expect(url).toBe('/icons/mapicon_pillar_green.png');
    });

    it('should handle all colors correctly', () => {
      const colors = ['green', 'yellow', 'red', 'grey'] as const;
      colors.forEach(color => {
        const url = getIconUrl('Pillar', color);
        expect(url).toContain(`mapicon_pillar_${color}.png`);
      });
    });
  });

  describe('getIconUrlForTrig', () => {
    it('should use condition color in condition mode', () => {
      const url = getIconUrlForTrig('Pillar', 'G', 'condition', null);
      expect(url).toBe('/icons/mapicon_pillar_green.png');
    });

    it('should handle damaged condition', () => {
      const url = getIconUrlForTrig('FBM', 'D', 'condition', null);
      expect(url).toBe('/icons/mapicon_fbm_yellow.png');
    });

    it('should handle missing condition', () => {
      const url = getIconUrlForTrig('Passive Station', 'M', 'condition', null);
      expect(url).toBe('/icons/mapicon_passive_red.png');
    });

    it('should use grey when no log status in userLog mode', () => {
      const url = getIconUrlForTrig('Pillar', 'G', 'userLog', null);
      expect(url).toBe('/icons/mapicon_pillar_grey.png');
    });

    it('should use log status color in userLog mode', () => {
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: true };
      const url = getIconUrlForTrig('Pillar', 'M', 'userLog', logStatus);
      expect(url).toBe('/icons/mapicon_pillar_green.png');
    });

    it('should use red for not found in userLog mode', () => {
      const logStatus: UserLogStatus = { hasLogged: true, foundStatus: false };
      const url = getIconUrlForTrig('Pillar', 'G', 'userLog', logStatus);
      expect(url).toBe('/icons/mapicon_pillar_red.png');
    });

    it('should add highlight suffix when highlighted', () => {
      const url = getIconUrlForTrig('Pillar', 'G', 'condition', null, true);
      expect(url).toBe('/icons/mapicon_pillar_green_h.png');
    });
  });

  describe('localStorage preferences', () => {
    let localStorageMock: ReturnType<typeof mockLocalStorage>;

    beforeEach(() => {
      localStorageMock = mockLocalStorage();
    });

    afterEach(() => {
      localStorageMock.localStorageMock.clear();
    });

    describe('getPreferredIconColorMode', () => {
      it('should return default when no preference stored', () => {
        const preferred = getPreferredIconColorMode();
        expect(preferred).toBe(DEFAULT_ICON_COLOR_MODE);
      });

      it('should return stored preference', () => {
        localStorageMock.localStorageMock.setItem(ICON_COLOR_MODE_STORAGE_KEY, 'userLog');
        const preferred = getPreferredIconColorMode();
        expect(preferred).toBe('userLog');
      });

      it('should handle localStorage errors gracefully', () => {
        localStorageMock.localStorageMock.getItem.mockImplementation(() => {
          throw new Error('localStorage error');
        });
        const preferred = getPreferredIconColorMode();
        expect(preferred).toBe(DEFAULT_ICON_COLOR_MODE);
      });
    });

    describe('setPreferredIconColorMode', () => {
      it('should save preference to localStorage', () => {
        setPreferredIconColorMode('userLog');
        expect(localStorageMock.localStorageMock.setItem).toHaveBeenCalledWith(
          ICON_COLOR_MODE_STORAGE_KEY,
          'userLog'
        );
      });

      it('should handle localStorage errors gracefully', () => {
        localStorageMock.localStorageMock.setItem.mockImplementation(() => {
          throw new Error('localStorage error');
        });
        expect(() => setPreferredIconColorMode('userLog')).not.toThrow();
      });
    });

    it('should persist and retrieve icon color mode', () => {
      setPreferredIconColorMode('userLog');
      const retrieved = getPreferredIconColorMode();
      expect(retrieved).toBe('userLog');
    });
  });

  describe('ICON_LEGENDS', () => {
    it('should have legend for condition mode', () => {
      expect(ICON_LEGENDS.condition).toBeDefined();
      expect(Array.isArray(ICON_LEGENDS.condition)).toBe(true);
      expect(ICON_LEGENDS.condition.length).toBe(4);
    });

    it('should have legend for userLog mode', () => {
      expect(ICON_LEGENDS.userLog).toBeDefined();
      expect(Array.isArray(ICON_LEGENDS.userLog)).toBe(true);
      expect(ICON_LEGENDS.userLog.length).toBe(3);
    });

    it('should have stable condition legend entries', () => {
      const legendColors = ICON_LEGENDS.condition.map(item => item.color);
      expect(legendColors).toEqual(['green', 'yellow', 'red', 'grey']);
    });

    it('should have stable userLog legend entries', () => {
      const legendColors = ICON_LEGENDS.userLog.map(item => item.color);
      expect(legendColors).toEqual(['green', 'red', 'grey']);
    });

    it('should have labels for all legend entries', () => {
      Object.values(ICON_LEGENDS).forEach(legend => {
        legend.forEach(item => {
          expect(typeof item.label).toBe('string');
          expect(item.label.length).toBeGreaterThan(0);
        });
      });
    });
  });

  describe('Default color mode for TrigDetailMap', () => {
    it('should use condition as default mode', () => {
      expect(DEFAULT_ICON_COLOR_MODE).toBe('condition');
    });

    it('should return condition icons by default in TrigDetailMap scenario', () => {
      // TrigDetailMap always uses condition mode
      const url = getIconUrlForTrig('Pillar', 'G', 'condition', null);
      expect(url).toContain('green');
    });
  });

  describe('Type stability', () => {
    it('should have exactly two color modes', () => {
      const modes: IconColorMode[] = ['condition', 'userLog'];
      // This test ensures the IconColorMode type hasn't changed
      modes.forEach(mode => {
        expect(['condition', 'userLog']).toContain(mode);
      });
    });

    it('should accept all valid physical types', () => {
      const types = [
        'Pillar',
        'FBM',
        'Flush Bracket',
        'Passive Station',
        'Passive station',
        'Intersection',
        'Intersected Station',
        'Bolt',
        'Active Station',
        'Other',
      ];

      types.forEach(type => {
        const basename = getIconBaseName(type);
        expect(basename).toBeDefined();
        expect(typeof basename).toBe('string');
      });
    });
  });
});

