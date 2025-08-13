export class UsageToDomainMapper {
  private readonly mapping: Record<string, string> = {
    DoorSensor: 'binary_sensor',
    Temperature: 'sensor',
  };

  map(usage?: string): string | undefined {
    if (!usage) {
      return undefined;
    }
    const direct = this.mapping[usage];
    if (direct) {
      return direct;
    }
    if (usage.toLowerCase().includes('light')) {
      return 'light';
    }
    if (usage.toLowerCase().includes('valve')) {
      return 'valve';
    }
    return undefined;
  }
}
