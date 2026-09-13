import rawPaths from './raw_state_paths.json';

export const RAW_STATE_PATHS: Record<string, { title: string; d: string }> = {};

for (const [key, pathStr] of Object.entries(rawPaths)) {
  RAW_STATE_PATHS[key] = {
    title: key.replace(/_/g, ' '),
    d: pathStr as string,
  };
}
