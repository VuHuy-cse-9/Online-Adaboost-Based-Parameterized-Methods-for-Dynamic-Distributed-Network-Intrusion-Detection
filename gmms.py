import numpy as np

class OnlineGMM:
    def __init__(self,
                std,
                n_components=1,
                T=0.5,
                epsilon = 1e-9
                ):
        """_Initialize parameters_
        
        Args:
            T (_float_) threshold used in equation (5)
        """
        self.n_components = n_components
        self.T = T
        self.default_std = std
        self.epsilon = epsilon
        
    def build(self, n_labels = 2):
        """Initialization of GMM components.
        
        Args:
            n_labels (_int_): _number of labels_
        Other:
            Default index 0 is normal classifier
        """
        self.n_labels = n_labels
        self.n_gmms = self.n_components * self.n_labels
        self.means = np.random.normal(loc=0, scale=1, size=(self.n_labels, self.n_components))
        # self.means = np.random.normal(loc=0, scale=1, size=(self.n_labels, self.n_components)) \
        #             * np.arange(n_labels).reshape((n_labels, 1))
        self.stds = np.ones((n_labels, self.n_components))
        self.weight = np.random.normal(loc=0, scale=1, size=(self.n_labels, self.n_components))
        self.N = np.ones((self.n_labels, self.n_components), dtype=np.int32)
        self.A = np.ones((self.n_labels, self.n_components))
    
    def _convert_label_to_index(self, label):
        if (label > 1) or (label == 0) or ((label * -1) > (self.n_labels - 1)):
            print("Error: label index out of bound")
            return None
        if label == 1:
            return 0
        return label * -1
        
    
    def predict_prob(self, x, class_index=None, gmms_indices = None):
        """_return probability of Gaussian_
        Args:
            x: (_float_): feature value of sample
            gmss_indices: (_array_like (int, )_): List of selected gmms's indices for predict 
        Variables:
            result: (_array-like (n_labels, n_components)_) probability of each GMM
        """
        
        if gmms_indices == None:
            return 1.0 / (self.stds[class_index] * np.sqrt(2 * np.pi)) * \
                    np.exp(-0.5 * ((x - self.means[class_index]) / self.stds[class_index]) ** 2) 
        return 1.0 / (self.stds[class_index, gmms_indices] * np.sqrt(2 * np.pi))  * \
            np.exp(-0.5 * ((x - self.means[class_index, gmms_indices]) / self.stds[class_index, gmms_indices]) ** 2) 
        
        
    def fit(self, x, y):
        """Updating Online GMM
        Args:
            x: (_float_): feature value of sample
        Variables:
            Tau (_array-like (nlabels, n_components_) binary value equation (5)
            Z   (_array-like (nlabels, )_) relation value between (x, y) and the GMM equation (8)
            relate_indices (_tuple of array_likes (n < nlabels, )_) indices of GMMS have Z > 0
            delta (_array-like (1, relate_indices, n_components)_) probability that (x, y) belong to ith 
                                                                component equation (9)
            t   (_array_like (nlabels, )_) indices of GMM's components have min weight
        """
        class_index = self._convert_label_to_index(y)
        #print("===========================================================")
        #print(f">> Class index: {class_index}")
        # Step 1: Update weight omega_j^y
        #print(f">> {np.abs((x - self.means) / self.stds)}")
        Tau = np.squeeze(np.abs((x - self.means[class_index, :]) / self.stds[class_index, :]) < self.T)
        if Tau.shape != (self.n_components, ):
            raise Exception(f"Tau shape should be: {(self.n_components, )}, instead {Tau.shape}")
        
        self.N[class_index] += Tau   
        
        self.weight[class_index] = self.N[class_index] / np.sum(self.N[class_index], keepdims=True)
        #print(f"weight: {self.weight}")
        
        if self.weight.shape != (self.n_labels, self.n_components):
            raise Exception(f"weight shape should be: {(self.n_labels, self.n_components)}, instead {self.weight.shape}")
        # Step 2: Calculate the relation between (x, y)
        Z = np.sum(
            self.weight[class_index] * self.predict_prob(x, class_index) * Tau
        )
        
        #print(f">> Z: {Z}")
        #print(f"predict_prob: {self.predict_prob(x)}")
        
        #print("-------------------------------------")
        if Z > 0:      
            # Step 3: Calculate the probability that (x, y) 
            # belongs to the ith component of the GMM.
            delta = \
                (self.weight[class_index] * self.predict_prob(x, class_index) * Tau) \
             / Z + self.epsilon
            if delta.shape != (self.n_components, ):
                raise Exception(f"delta shape should be: {(self.n_labels, self.n_components)}, instead {delta.shape}")
            
            self.A[class_index] += delta
            #print(f">> delta: {delta}")
            #print(f">> A:  {self.A}")
            
            # Step 4: Update parameters for each components
            self.means[class_index] = \
                    ((self.A[class_index] - delta) * self.means[class_index]  + delta * x) \
                    / self.A[class_index]
            #print(f">> means: {self.means}")
            """
            CAUTION: EASILY TO OVERFLOW
            """  
            self.stds[class_index] = np.sqrt(
                ((self.A[class_index] - delta) * (self.stds[class_index] ** 2)) / self.A[class_index]  \
                + ((self.A[class_index] - delta) * delta * (x - self.means[class_index]) ** 2) / self.A[class_index]**2)
            #print(f">> stds: {self.stds}")
        
        else:
            # Step 5: Reset parameters of the weakest components
            t = np.argmin(self.weight[class_index])
            self.N[class_index, t] += 1
            self.A[class_index, t] += 1
            self.means[class_index, t] = x
            self.stds[class_index, t] = self.default_std
    
    def predict(self, x):
        """Return predcited class
        Args:
            x (_(nsamples, )_ or (nsamples, 1)): _feature value_
        return 
        """
        if not np.isscalar(x):
            x = x[:, None]
            probs = []
            for class_index in range(self.n_labels):
                probs.append(np.sum(self.weight[class_index] * self.predict_prob(x, class_index), axis=1))
            probs = np.transpose(probs, (1, 0))
            result = np.array(np.min(probs[:, 0, None] - (probs[:, 1:] / (self.n_labels - 1)), axis=1) > 0, np.int32) #(Nsamples,)
            result[result == 0] = -1
            
            if result.shape != (x.shape[0],):
                raise Exception(f"Shape predict is not right: {result.shape}")
            return result
        else:
            probs = []
            for class_index in range(self.n_labels):
                probs.append(np.sum(self.weight[class_index] * self.predict_prob(x, class_index)))
            probs = np.array(probs)
            #print(probs)
            if np.min(probs[0] - (probs[1:] / (self.n_labels - 1))) > 0: #How can we know the fist index is labels zeros???
                return 1
            return -1
        
    def get_parameters(self):
        return {
            "nlabel": self.n_labels,
            "ncomponent": self.n_components,
            "means": self.means.tolist(),
            "stds": self.stds.tolist(),
            "weights": self.weight.tolist(),
        }
        
    def set_parameters(self, model_para):
        self.n_labels = model_para["nlabel"]
        self.n_components = model_para["ncomponent"]
        self.means = np.array(model_para["means"], np.float64)
        self.stds = np.array(model_para["stds"], np.float64)
        self.weight = np.array(model_para["weights"], np.float64)
        
    def get_avg_means(self):
        avg_means = np.mean(self.weight * self.means, axis=1)
        return avg_means

    def get_avg_stds(self):
        avg_stds = np.mean(self.weight * self.stds, axis=1)
        return avg_stds