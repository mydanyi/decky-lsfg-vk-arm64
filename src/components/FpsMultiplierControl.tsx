import { PanelSectionRow, DialogButton, Focusable, Dropdown, SliderField } from "@decky/ui";
import { ConfigurationData } from "../config/configSchema";
import {
  GENERATION_MODE, MULTIPLIER, TARGET_FPS, TARGET_MAX_MULTIPLIER
} from "../config/generatedConfigSchema";
import t from '../i18n/i18n';

interface FpsMultiplierControlProps {
  config: ConfigurationData;
  onConfigChange: (fieldName: keyof ConfigurationData, value: boolean | number | string) => Promise<void>;
}

export function FpsMultiplierControl({
  config,
  onConfigChange
}: FpsMultiplierControlProps) {
  const isTarget = config.generation_mode === 'target';
  const modes = [
    { data: 'fixed', label: t('GENERATION_MODE_FIXED', 'Fixed Multiplier') },
    { data: 'target', label: t('GENERATION_MODE_TARGET', 'Target FPS') }
  ];
  return (
    <>
      <PanelSectionRow>
        <Dropdown
          menuLabel={t('GENERATION_MODE_LABEL', 'Generation Mode')}
          rgOptions={modes}
          selectedOption={config.generation_mode}
          onChange={(option: { data: string }) => onConfigChange(GENERATION_MODE, option.data)}
        />
      </PanelSectionRow>

      {isTarget ? (
        <>
          <PanelSectionRow>
            <SliderField
              label={`${t('TARGET_FPS_LABEL', 'Target FPS')} (${config.target_fps} FPS)`}
              description={t('TARGET_FPS_DESC',
                'Desired output frame rate. Original frames are kept when the game already reaches it.')}
              value={config.target_fps}
              min={30}
              max={240}
              step={1}
              onChange={(value: number) => onConfigChange(TARGET_FPS, Math.round(value))}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <SliderField
              label={`${t('TARGET_MAX_MULTIPLIER_LABEL', 'Maximum Multiplier')} (${config.target_max_multiplier}X)`}
              description={t('TARGET_MAX_MULTIPLIER_DESC',
                'Highest frame multiplier allowed while chasing the target.')}
              value={config.target_max_multiplier}
              min={2}
              max={4}
              step={1}
              onChange={(value: number) => onConfigChange(TARGET_MAX_MULTIPLIER, Math.round(value))}
            />
          </PanelSectionRow>
        </>
      ) : (
        <PanelSectionRow>
          <Focusable
          style={{
            marginTop: "6px",
            marginBottom: "6px",
            display: "flex",
            justifyContent: "center",
            alignItems: "center"
          }}
          flow-children="horizontal"
        >
          <DialogButton
            style={{
              marginLeft: "0px",
              height: "30px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "5px 0px 0px 0px",
              minWidth: "40px",
            }}
            onClick={() => onConfigChange(MULTIPLIER, Math.max(1, config.multiplier - 1))}
            disabled={config.multiplier <= 1}
          >
            −
          </DialogButton>
          <div
            style={{
              marginLeft: "20px",
              marginRight: "20px",
              fontSize: "16px",
              fontWeight: "bold",
              color: config.multiplier > 4 ? "red" : "white",
              minWidth: "60px",
              textAlign: "center"
            }}
          >
            {config.multiplier < 2 ? t('MULTIPLIER_OFF', 'OFF') : `${config.multiplier}X`}
          </div>
          <DialogButton
            style={{
              marginLeft: "0px",
              height: "30px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "5px 0px 0px 0px",
              minWidth: "40px",
            }}
            onClick={() => onConfigChange(MULTIPLIER, Math.min(4, config.multiplier + 1))}
            disabled={config.multiplier >= 4}
          >
            +
          </DialogButton>
          </Focusable>
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <div
          style={{
            fontSize: "11px",
            lineHeight: "1.3",
            opacity: 0.6,
            textAlign: "center"
          }}
        >
          {t('MULTIPLIER_RESTART_NOTE', 'Turning frame generation on or off requires restarting the game.')}
        </div>
      </PanelSectionRow>
    </>
  );
}
