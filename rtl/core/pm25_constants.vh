// Frozen constants for pm25_core_v1_adaptive_bias_fixed.
// This include contains constants only; it intentionally defines no module.
localparam integer PM25_SCALE = 16;
localparam signed [31:0] PM25_MIN_X16 = 32'sd0;
localparam signed [31:0] PM25_MAX_X16 = 32'sd8000;
localparam signed [31:0] BIAS_MIN_X16 = -32'sd2048;
localparam signed [31:0] BIAS_MAX_X16 = 32'sd2048;
localparam signed [31:0] GOOD_MAX_X16 = 32'sd192;
localparam signed [31:0] MODERATE_MAX_X16 = 32'sd566;
localparam signed [31:0] USG_MAX_X16 = 32'sd886;
localparam signed [31:0] UNHEALTHY_MAX_X16 = 32'sd2406;
localparam signed [31:0] ALERT_ON_X16 = 32'sd566;
localparam signed [31:0] ALERT_OFF_X16 = 32'sd512;
