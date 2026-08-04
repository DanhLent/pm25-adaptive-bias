// Simple 8N1 UART receiver for the laptop-only PM2.5 demo.
module uart_rx (
    clk,
    rst_n,
    rx,
    data_valid,
    data_byte
);

parameter integer CLK_FREQ_HZ = 27000000;
parameter integer BAUD_RATE = 115200;
localparam integer CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE;
localparam integer HALF_BIT_CLKS = CLKS_PER_BIT / 2;

input clk;
input rst_n;
input rx;
output reg data_valid;
output reg [7:0] data_byte;

localparam [1:0] STATE_IDLE = 2'd0;
localparam [1:0] STATE_START = 2'd1;
localparam [1:0] STATE_DATA = 2'd2;
localparam [1:0] STATE_STOP = 2'd3;

reg [1:0] state;
reg rx_meta;
reg rx_sync;
reg [15:0] clk_count;
reg [2:0] bit_index;
reg [7:0] data_shift;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        rx_meta <= 1'b1;
        rx_sync <= 1'b1;
    end else begin
        rx_meta <= rx;
        rx_sync <= rx_meta;
    end
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= STATE_IDLE;
        clk_count <= 16'd0;
        bit_index <= 3'd0;
        data_shift <= 8'd0;
        data_byte <= 8'd0;
        data_valid <= 1'b0;
    end else begin
        data_valid <= 1'b0;

        case (state)
            STATE_IDLE: begin
                clk_count <= 16'd0;
                bit_index <= 3'd0;
                if (!rx_sync) begin
                    state <= STATE_START;
                end
            end

            STATE_START: begin
                if (clk_count == HALF_BIT_CLKS[15:0]) begin
                    clk_count <= 16'd0;
                    if (!rx_sync) begin
                        state <= STATE_DATA;
                    end else begin
                        state <= STATE_IDLE;
                    end
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end

            STATE_DATA: begin
                if (clk_count == (CLKS_PER_BIT - 1)) begin
                    clk_count <= 16'd0;
                    data_shift[bit_index] <= rx_sync;
                    if (bit_index == 3'd7) begin
                        bit_index <= 3'd0;
                        state <= STATE_STOP;
                    end else begin
                        bit_index <= bit_index + 3'd1;
                    end
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end

            STATE_STOP: begin
                if (clk_count == (CLKS_PER_BIT - 1)) begin
                    clk_count <= 16'd0;
                    state <= STATE_IDLE;
                    if (rx_sync) begin
                        data_byte <= data_shift;
                        data_valid <= 1'b1;
                    end
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end

            default: begin
                state <= STATE_IDLE;
            end
        endcase
    end
end

endmodule
