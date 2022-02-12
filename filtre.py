
"""Ce script est un exemple de matplotlib"""

import numpy as np


def moving_average(x, n, type_='simple'):
    """
    compute an n period moving average.

    type is 'simple' | 'exponential'

    """
    x = np.asarray(x)
    if type_ == 'simple':
        weights = np.ones(n)
    else:
        weights = np.exp(np.linspace(-1., 0., n))

    weights /= weights.sum()

    a_liss = np.convolve(x, weights, mode='full')[:len(x)]
    a_liss[:n] = a_liss[n]

    return a_liss


def get_a_b(x1, y1, x2, y2):
    a = (y1 - y2)/(x1 - x2)
    b = y1 - a*x1
    return a, b


if __name__ == '__main__':

    import matplotlib.pyplot as plt

    data = [1300,1474,1532,1576,1643,1737,1817,1895,1919,2018,2047,2069,2118,2164,2290,2329,2404,2463,2524,2587,2626,2664,2716,2739,2771,2810,2847,2858,2894,2901,2926,2963,2995,2989,2995,2997,2995,3006,3003,2994,3001,2999,3002,2986,2984,2986,2989,2980,2937,2924,2933,2912,2905,2878,2860,2838,2832,2823,2809,2806,2793,2791,2786,2787,2789,2786,2803,2795,2798,2806,2802,2799,2802,2797,2799,2798,2785,2789,2790,2789,2784,2796,2797,2809,2812,2816,2820,2834,2837,2818,2823,2823,2823,2829,2826,2817,2832,2835,2834,2836,2821,2834,2827,2828,2830,2826,2834,2827,2833,2827,2831,2837,2824,2832,2832,2834,2829,2824,2839,2827,2819,2830,2829,2820,2836,2832,2829,2835,2829,2829,2819,2823,2828,2832,2831,2838,2830,2828,2828,2827,2833,2838,2839,2848,2851,2866,2867,2867,2872,2882,2900,2908,2931,2953,2962,2969,2994,3028,3058,3068,3092,3117,3138,3128,3136,3150,3147,3161,3167,3184,3181,3182,3180,3196,3182,3190,3184,3186,3186,3194,3189,3189,3184,3190,3188,3197,3182,3181,3195,3188,3188,3185,3185,3187,3195,3186,3187,3186,3184,3190,3181,3188,3182,3174,3181,3180,3183,3186,3175,3175,3166,3169,3181,3178,3165,3168,3168,3160,3161,3146,3136,3117,3092,3065,3027,2992,2958,2931,2892,2850,2800,2757,2722,2705,2689,2585,2658,2654,2629,2625,2622,2620,2620,2599,2600,2600,2599,2594,2603,2588,2598,2594,2604,2596,2597,2596,2589,2594,2590,2596,2586,2590,2586,2585,2576,2581,2587,2580,2568,2582,2568,2573,2559,2553,2532,2496,2465,2421,2355,2306,2248,2146,2129,2016,1949,1890,1843,1759,1613,1592,1477,1429,1411,1351]

    print(len(data))  # 294

    l = 9
    average5 = []
    for i in range(200):
        d = []
        for j in range(l):
            d.append(data[i + j])
        d = np.array(d)
        m = moving_average(d, 8, type_='expo')
        average5.append(int(m[0]))

    l = 28
    average2 = []
    for i in range(200):
        d = []
        for j in range(l):
            d.append(data[i + j])
        d = np.array(d)
        m = moving_average(d, 9, type_='simple')
        average2.append(int(m[0]))

    l = 28
    average3 = []
    for i in range(200):
        d = []
        for j in range(l):
            d.append(data[i + j])
        d = np.array(d)
        m = moving_average(d, 27, type_='simple')
        average3.append(int(m[0]))

    fig, ax = plt.subplots(1, figsize=(8, 6))
    fig.suptitle('Multiple Lines in Same Plot', fontsize=15)

    x = [i for i in range(200)]
    y1 = data[:200]
    ax.plot(x, y1, color='r')

    x1 = [i+5 for i in x]

    histo = [0]*32
    yf = []
    for d in data:
        histo.append(d)
        del histo[0]

        try:
            d = int(moving_average( np.array(histo),
                                    31,
                                    type_='simple')[0])
        except:
            print("Erreur moving_average depth")

        # Pour bien comprendre
        mini = 1000 + 100
        maxi = 8000 - 300
        lenght = 39750

        # Voir le dessin
        a, b = get_a_b(mini, 0, maxi, lenght)
        frame = int(a*d + b)

        # Inversion de la video
        frame = lenght - frame
        # Pour ne jamais planté
        if frame < 0:
            frame = 0
        if frame >= lenght:
            frame = lenght - 1
        # # # Pile des 8 dernières valeurs lissées
        # # self.histo_slow.append(frame)
        # # del self.histo_slow[0]
        # # try:
            # # frame = int(moving_average( np.array(self.histo_slow),
                                        # # self.slow_size - 1,
                                        # # type_='simple')[0])
        # # except:
            # # print("Erreur moving_average depth")
        # # print(frame, self.histo_slow)
        yf.append(frame)
    y1 = yf[:200]

    # # ax.plot(x1, average5, color='b')
    ax.plot(x1, average2, color='m')
    ax.plot(x1, average3, color='g')
    ax.plot(x1, y1, color='k')

    plt.show()
